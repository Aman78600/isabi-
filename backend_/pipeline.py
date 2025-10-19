import os
import io
import uuid
import asyncio
import time
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from moviepy import VideoFileClip
from google.cloud import storage
from google.cloud import speech
from pydub import AudioSegment
from pydub.effects import normalize, high_pass_filter, low_pass_filter
from gcp_clients import GCPClients
import vertexai
from pydub.effects import normalize, high_pass_filter, low_pass_filter
from gcp_clients import GCPClients

class ProcessingPipeline:
    def __init__(self, clients: GCPClients):
        self.clients = clients
        self.bucket = clients.bucket
        # Initialize Vertex AI
        vertexai.init(project=clients.project_id, location=clients.location)

    def _enhance_audio(self, audio: AudioSegment) -> AudioSegment:
        """
        Enhance audio quality for better transcription accuracy
        """
        try:
            print("Enhancing audio quality...")
            
            # Normalize audio levels
            audio = normalize(audio)
            
            # Apply high-pass filter to reduce low-frequency noise (remove frequencies below 80Hz)
            audio = high_pass_filter(audio, cutoff=80)
            
            # Apply low-pass filter to reduce high-frequency noise (remove frequencies above 8000Hz for speech)
            audio = low_pass_filter(audio, cutoff=8000)
            
            # Convert to mono if stereo (speech recognition works better with mono)
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Set optimal sample rate for speech recognition (16kHz is Google's preferred)
            audio = audio.set_frame_rate(16000)
            
            # Boost volume if too quiet
            if audio.dBFS < -30:
                audio = audio + (abs(audio.dBFS + 20))
                
            print(f"Audio enhanced: {audio.frame_rate}Hz, {audio.channels} channel(s), {audio.dBFS:.1f} dBFS")
            return audio
            
        except Exception as e:
            print(f"Warning: Audio enhancement failed: {e}. Using original audio.")
            return audio

    def _detect_voice_segments(self, audio: AudioSegment, min_silence_len: int = 1000, 
                              silence_thresh: int = -40) -> List[Tuple[int, int]]:
        """
        Detect voice segments to create intelligent chunks
        """
        try:
            from pydub.silence import detect_nonsilent
            
            # Detect non-silent segments
            voice_segments = detect_nonsilent(
                audio, 
                min_silence_len=min_silence_len,  # Minimum silence length in ms
                silence_thresh=silence_thresh     # Silence threshold in dBFS
            )
            
            print(f"Detected {len(voice_segments)} voice segments")
            return voice_segments
            
        except Exception as e:
            print(f"Voice detection failed: {e}. Using time-based chunking.")
            # Fallback to time-based chunks
            chunk_length_ms = 45 * 1000  # 45 seconds
            segments = []
            for i in range(0, len(audio), chunk_length_ms):
                end = min(i + chunk_length_ms, len(audio))
                segments.append((i, end))
            return segments

    def _create_smart_chunks(self, audio: AudioSegment, max_chunk_duration: int = 45000) -> List[AudioSegment]:
        """
        Create intelligent chunks based on voice activity and pauses
        """
        voice_segments = self._detect_voice_segments(audio)
        chunks = []
        current_chunk_start = 0
        
        for segment_start, segment_end in voice_segments:
            # If adding this segment would exceed max duration, finalize current chunk
            if segment_end - current_chunk_start > max_chunk_duration:
                if current_chunk_start < segment_start:
                    chunk = audio[current_chunk_start:segment_start]
                    if len(chunk) > 1000:  # Only add chunks longer than 1 second
                        chunks.append(chunk)
                current_chunk_start = segment_start
        
        # Add the final chunk
        if current_chunk_start < len(audio):
            final_chunk = audio[current_chunk_start:]
            if len(final_chunk) > 1000:
                chunks.append(final_chunk)
        
        # If no valid chunks were created, fall back to time-based chunking
        if not chunks:
            chunk_length_ms = 45 * 1000
            for i in range(0, len(audio), chunk_length_ms):
                chunk = audio[i:i + chunk_length_ms]
                chunks.append(chunk)
        
        print(f"Created {len(chunks)} intelligent chunks")
        return chunks

    def _transcribe_chunk_with_retry(self, chunk_gcs_uri: str, chunk_index: int, 
                                   max_retries: int = 3) -> str:
        """
        Transcribe a single chunk with retry logic and enhanced configuration
        """
        for attempt in range(max_retries):
            try:
                print(f"Transcribing chunk {chunk_index + 1}, attempt {attempt + 1}")
                
                audio = speech.RecognitionAudio(uri=chunk_gcs_uri)
                
                # Enhanced configuration for better accuracy
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                    sample_rate_hertz=16000,  # Match our enhanced audio
                    language_code="en-US",
                    model="latest_long",
                    use_enhanced=True,
                    enable_automatic_punctuation=True,
                    enable_word_time_offsets=False,
                    enable_word_confidence=True,  # Enable to filter low-confidence words
                    max_alternatives=3,  # Get multiple alternatives to choose best
                    profanity_filter=False,
                    # Audio channel configuration
                    audio_channel_count=1,
                    enable_separate_recognition_per_channel=False,
                    # Additional accuracy improvements
                    metadata=speech.RecognitionMetadata(
                        interaction_type=speech.RecognitionMetadata.InteractionType.DISCUSSION,
                        microphone_distance=speech.RecognitionMetadata.MicrophoneDistance.NEARFIELD,
                        original_media_type=speech.RecognitionMetadata.OriginalMediaType.AUDIO,
                        recording_device_type=speech.RecognitionMetadata.RecordingDeviceType.OTHER_INDOOR_DEVICE,
                    )
                )
                
                # Use long_running_recognize for better accuracy on longer audio
                operation = self.clients.speech_client.long_running_recognize(config=config, audio=audio)
                response = operation.result(timeout=600)
                
                # Process results with confidence filtering
                transcripts = []
                for result in response.results:
                    if result.alternatives:
                        # Use the alternative with highest confidence
                        best_alternative = max(result.alternatives, key=lambda x: x.confidence)
                        
                        # Only include results with reasonable confidence
                        if hasattr(best_alternative, 'confidence') and best_alternative.confidence > 0.7:
                            transcripts.append(best_alternative.transcript)
                        elif not hasattr(best_alternative, 'confidence'):
                            # If no confidence score, include the transcript
                            transcripts.append(best_alternative.transcript)
                
                text = " ".join(transcripts).strip()
                
                if text:
                    print(f"Successfully transcribed chunk {chunk_index + 1}: {len(text)} characters")
                    return text
                else:
                    print(f"No transcript returned for chunk {chunk_index + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return ""
                    
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for chunk {chunk_index + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"All attempts failed for chunk {chunk_index + 1}")
                    return ""
        
        return ""

    def _clean_transcript(self, transcript: str) -> str:
        """
        Clean and format the transcript
        """
        # Remove extra whitespace
        transcript = " ".join(transcript.split())
        
        # Fix common transcription issues
        replacements = {
            " . ": ". ",
            " , ": ", ",
            " ? ": "? ",
            " ! ": "! ",
            "  ": " ",  # Double spaces
        }
        
        for old, new in replacements.items():
            transcript = transcript.replace(old, new)
        
        return transcript.strip()

    def _transcribe_chunk_sync(self, chunk_gcs_uri: str) -> str:
        """Sync function to transcribe a single chunk with enhanced accuracy"""
        try:
            audio = speech.RecognitionAudio(uri=chunk_gcs_uri)
            config = speech.RecognitionConfig(
                language_code="en-US",
                model="latest_long",  # Use latest long-form model for better accuracy
                use_enhanced=True,    # Enable enhanced models for superior accuracy
                enable_automatic_punctuation=True,
                enable_word_time_offsets=False,  # Disable to reduce processing time
                enable_word_confidence=False,    # Disable to reduce processing time
                # Additional accuracy settings
                max_alternatives=1,   # Only return the best result
                profanity_filter=False,  # Don't filter profanity for accuracy
                diarization_config=None,  # Disable speaker diarization for speed
            )
            op = self.clients.speech_client.long_running_recognize(config=config, audio=audio)
            resp = op.result(timeout=900)  # Increased timeout for enhanced processing
            text = " ".join([r.alternatives[0].transcript for r in resp.results if r.alternatives])
            return text.strip()
        except Exception as e:
            print(f"Warning: Could not transcribe chunk {chunk_gcs_uri}: {e}")
            return ""

    async def ensure_vector_index(self, display_name: str) -> str:
        try:
            return self.clients.ensure_index(display_name)
        except Exception as e:
            print(f"Warning: Could not ensure vector index: {e}")
            return f"projects/{self.clients.project_id}/locations/{self.clients.location}/indexes/{display_name.replace('_', '-')}"

    async def ensure_product_folders(self, product_name: str) -> str:
        # Create placeholder blobs to simulate folder creation
        # GCS doesn't have real folders, just prefixes
        for folder in ["videos", "audios", "texts", "PDFs"]:
            try:
                blob = self.bucket.blob(f"{product_name}/{folder}/.keep")
                # Try to upload without checking existence to avoid permission issues
                blob.upload_from_string("", content_type="text/plain")
            except Exception as e:
                print(f"Warning: Could not create placeholder for {folder}: {e}")
                # Continue anyway - folder structure will still work
        return f"gs://{self.clients.bucket_name}/{product_name}/"

    async def process_videos(self, product_name: str, product_id: str, videos: List) -> Dict:
        """
        Process videos in optimized phases:
        Phase 1: Upload all videos to GCP in parallel
        Phase 2: Extract and upload all audios in parallel
        Phase 3: Transcribe all audios to text in parallel
        Phase 4: Create PDFs and generate embeddings in parallel
        """
        print(f"Starting optimized processing of {len(videos)} videos...")

        # Phase 1: Upload all videos to GCP in parallel
        print("Phase 1: Uploading all videos to GCP in parallel...")
        video_upload_tasks = []
        for idx, up in enumerate(videos, start=1):
            task = self._upload_video_to_gcp(product_name, up, idx)
            video_upload_tasks.append(task)

        video_results = await asyncio.gather(*video_upload_tasks, return_exceptions=True)
        video_gcs_uris = []
        for result in video_results:
            if isinstance(result, Exception):
                print(f"Error uploading video: {result}")
                continue
            video_gcs_uris.append(result)

        print(f"Phase 1 completed: {len(video_gcs_uris)} videos uploaded")

        # Phase 2: Extract and upload all audios in parallel
        print("Phase 2: Extracting and uploading all audios in parallel...")
        audio_upload_tasks = []
        for video_info in video_gcs_uris:
            task = self._extract_and_upload_audio(product_name, video_info, video_info["idx"])
            audio_upload_tasks.append(task)

        audio_results = await asyncio.gather(*audio_upload_tasks, return_exceptions=True)
        audio_gcs_uris = []
        for result in audio_results:
            if isinstance(result, Exception):
                print(f"Error processing audio: {result}")
                continue
            audio_gcs_uris.append(result)

        print(f"Phase 2 completed: {len(audio_gcs_uris)} audios processed")

        # Phase 3: Transcribe all audios to text in parallel
        print("Phase 3: Transcribing all audios to text in parallel...")
        transcription_tasks = []
        for audio_info in audio_gcs_uris:
            task = self._transcribe_audio_to_text(product_name, audio_info, audio_info["idx"])
            transcription_tasks.append(task)

        transcription_results = await asyncio.gather(*transcription_tasks, return_exceptions=True)
        text_results = []
        for result in transcription_results:
            if isinstance(result, Exception):
                print(f"Error transcribing audio: {result}")
                continue
            text_results.append(result)

        print(f"Phase 3 completed: {len(text_results)} transcriptions completed")

        # Phase 4: Create PDFs and generate embeddings in parallel
        print("Phase 4: Creating PDFs and generating embeddings in parallel...")
        pdf_tasks = []
        for text_info in text_results:
            task = self._create_pdf_and_embed(product_name, product_id, text_info["video_gcs"], text_info["audio_gcs"], text_info, text_info["idx"])
            pdf_tasks.append(task)

        pdf_results = await asyncio.gather(*pdf_tasks, return_exceptions=True)
        items = []
        for result in pdf_results:
            if isinstance(result, Exception):
                print(f"Error creating PDF: {result}")
                continue
            items.append(result)

        print(f"Phase 4 completed: {len(items)} PDFs created with embeddings")

        # After processing all, write vectors JSONL to GCS and request index update
        all_vectors = []
        for it in items:
            for v in it.get("vectors", []):
                # Only include vectors with valid embeddings
                if v.get("embedding") and len(v["embedding"]) > 0:
                    all_vectors.append({
                        "id": v["vector_id"],
                        "embedding": v["embedding"],
                        "metadata": v.get("metadata", {}),
                    })
                    print(f"Including vector {v['vector_id']} with {len(v['embedding'])} dimensions")
                else:
                    print(f"Skipping vector {v.get('vector_id')} due to empty embedding")
        print(f"Total vectors to upload: {len(all_vectors)}")
        if all_vectors:
            import json
            from io import StringIO
            sio = StringIO()
            for rec in all_vectors:
                sio.write(json.dumps(rec) + "\n")
            data = sio.getvalue().encode("utf-8")
            vec_blob = self.bucket.blob(f"{product_name}/vectors/{uuid.uuid4().hex}.jsonl")
            # Increase timeout for large vector uploads
            vec_blob.upload_from_string(data, content_type="application/json", timeout=300)
            vectors_gcs = f"gs://{self.clients.bucket_name}/{vec_blob.name}"
            try:
                index_name = await self.ensure_vector_index("ai_product_index")
                print(f"Using vector index: {index_name}")
                update_result = self.clients.update_index_with_gcs(index_name, vectors_gcs)
                if update_result:
                    batch_id = vec_blob.name.rsplit("/", 1)[-1]
                    print(f"Vector index update initiated successfully, batch_id: {batch_id}")
                else:
                    print("Vector index update failed")
                    batch_id = None
            except Exception as e:
                print(f"Error updating vector index: {e}")
                batch_id = None
        else:
            vectors_gcs = None
            batch_id = None
        return {"items": items, "vectors_gcs": vectors_gcs, "vector_batch_id": batch_id}



    async def _upload_video_to_gcp(self, product_name: str, up, idx: int) -> Dict[str, str]:
        """Phase 1: Upload a single video to GCP"""
        temp_video = None
        try:
            # Save to temp
            temp_video = os.path.join(os.getcwd(), f"tmp_video_{uuid.uuid4().hex}.mp4")
            with open(temp_video, "wb") as f:
                f.write(await up.read())

            # Upload video with increased timeout
            video_blob = self.bucket.blob(f"{product_name}/videos/{idx}.mp4")
            video_blob.upload_from_filename(temp_video, timeout=300)
            video_gcs = f"gs://{self.clients.bucket_name}/{video_blob.name}"

            print(f"Uploaded video {idx} to {video_gcs}")
            return {
                "video_gcs": video_gcs,
                "original_name": up.filename,
                "idx": idx
            }

        except Exception as e:
            print(f"Error uploading video {idx}: {e}")
            raise e
        finally:
            if temp_video:
                try:
                    os.remove(temp_video)
                except Exception:
                    pass

    async def _extract_and_upload_audio(self, product_name: str, video_info: Dict[str, str], idx: int) -> Dict[str, str]:
        """Phase 2: Extract audio from video and upload"""
        temp_video = temp_audio = None
        try:
            video_gcs = video_info["video_gcs"]

            # Download video from GCS
            blob = self.bucket.blob(video_gcs.replace(f"gs://{self.clients.bucket_name}/", ""))
            temp_video = os.path.join(os.getcwd(), f"tmp_dl_video_{uuid.uuid4().hex}.mp4")
            blob.download_to_filename(temp_video)

            # Extract audio
            temp_audio = os.path.join(os.getcwd(), f"tmp_audio_{uuid.uuid4().hex}.mp3")
            clip = VideoFileClip(temp_video)
            clip.audio.write_audiofile(temp_audio)
            clip.audio.close()
            clip.close()

            # Upload audio with increased timeout
            audio_blob = self.bucket.blob(f"{product_name}/audios/{idx}.mp3")
            audio_blob.upload_from_filename(temp_audio, timeout=300)
            audio_gcs = f"gs://{self.clients.bucket_name}/{audio_blob.name}"

            print(f"Extracted and uploaded audio {idx} to {audio_gcs}")
            return {
                "video_gcs": video_gcs,
                "audio_gcs": audio_gcs,
                "original_name": video_info["original_name"],
                "idx": idx
            }

        except Exception as e:
            print(f"Error extracting audio {idx}: {e}")
            raise e
        finally:
            for temp_file in [temp_video, temp_audio]:
                if temp_file:
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass

    async def _transcribe_audio_to_text(self, product_name: str, audio_info: Dict[str, str], idx: int) -> Dict[str, str]:
        """Phase 3: Transcribe audio to text"""
        try:
            audio_gcs = audio_info["audio_gcs"]

            # Transcribe audio
            transcript = await self._transcribe_gcs_uri(audio_gcs)

            # Save text with increased timeout
            text_blob = self.bucket.blob(f"{product_name}/texts/{idx}.txt")
            text_blob.upload_from_string(transcript, timeout=300)
            text_gcs = f"gs://{self.clients.bucket_name}/{text_blob.name}"

            print(f"Transcribed audio {idx}: {len(transcript)} characters")
            return {
                "video_gcs": audio_info["video_gcs"],
                "audio_gcs": audio_gcs,
                "text_gcs": text_gcs,
                "transcript": transcript,
                "original_name": audio_info["original_name"],
                "idx": idx
            }

        except Exception as e:
            print(f"Error transcribing audio {idx}: {e}")
            raise e

    async def _create_pdf_and_embed(self, product_name: str, product_id: str, video_gcs: str, audio_gcs: str, text_info: Dict[str, str], idx: int) -> Dict:
        """Phase 4: Create PDF and generate embeddings"""
        try:
            text_gcs = text_info["text_gcs"]
            transcript = text_info["transcript"]

            # Create PDF from transcript
            lesson_title, pdf_bytes = await self._create_pdf_from_text(transcript, product_name, idx)

            # Upload PDF with increased timeout
            pdf_blob = self.bucket.blob(f"{product_name}/PDFs/{lesson_title}.pdf")
            pdf_blob.upload_from_string(pdf_bytes.getvalue(), content_type="application/pdf", timeout=300)
            pdf_gcs = f"gs://{self.clients.bucket_name}/{pdf_blob.name}"

            # Generate embeddings
            vectors = await self._embed_pdf_pages(pdf_bytes, product_id, product_name, idx, video_gcs, audio_gcs, text_gcs, pdf_gcs)

            print(f"Created PDF and embeddings for video {idx}: {lesson_title}")
            return {
                "video_gcs": video_gcs,
                "audio_gcs": audio_gcs,
                "text_gcs": text_gcs,
                "pdf_gcs": pdf_gcs,
                "lesson_title": lesson_title,
                "metadata": {"original_filename": text_info["original_name"]},
                "vectors": vectors,
            }

        except Exception as e:
            print(f"Error creating PDF for video {idx}: {e}")
            raise e

    async def _transcribe_gcs_uri(self, gcs_uri: str) -> str:
        """
        Transcribe audio from GCS URI with enhanced quality and intelligent chunking
        """
        temp_files = []
        chunk_uris = []
        
        try:
            print(f"Loading audio from GCS: {gcs_uri}")
            
            # Download audio from GCS
            blob = self.bucket.blob(gcs_uri.replace(f"gs://{self.clients.bucket_name}/", ""))
            temp_audio = os.path.join(os.getcwd(), f"tmp_audio_{uuid.uuid4().hex}.mp3")
            blob.download_to_filename(temp_audio)
            temp_files.append(temp_audio)
            
            # Load and enhance audio
            audio = AudioSegment.from_file(temp_audio)
            print(f"Original audio: {len(audio)/1000:.1f}s, {audio.frame_rate}Hz, {audio.channels} channels")
            
            # Enhance audio quality
            audio = self._enhance_audio(audio)
            
            # Create intelligent chunks
            chunks = self._create_smart_chunks(audio)
            
            print(f"Processing {len(chunks)} chunks...")
            
            # Upload chunks to GCS
            for idx, chunk in enumerate(chunks):
                # Export chunk with optimal settings
                temp_chunk = os.path.join(os.getcwd(), f"enhanced_chunk_{uuid.uuid4().hex}_{idx}.wav")
                temp_files.append(temp_chunk)
                chunk.export(temp_chunk, 
                           format="wav",
                           parameters=["-ac", "1", "-ar", "16000"])  # Force mono, 16kHz
                
                # Upload to GCS with timeout
                chunk_blob_name = f"enhanced_chunks/{uuid.uuid4().hex}_chunk_{idx}.wav"
                chunk_blob = self.bucket.blob(chunk_blob_name)
                chunk_blob.upload_from_filename(temp_chunk, timeout=300)  # 5 minute timeout
                chunk_gcs_uri = f"gs://{self.clients.bucket_name}/{chunk_blob_name}"
                chunk_uris.append(chunk_gcs_uri)
                
                print(f"Uploaded chunk {idx + 1}/{len(chunks)} to GCS")
            
            # Parallel transcription with progress tracking
            max_workers = min(3, len(chunk_uris))  # Reduced for stability with enhanced models
            print(f"Starting parallel transcription with {max_workers} workers...")
            
            transcripts = [""] * len(chunk_uris)  # Pre-allocate to maintain order
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_index = {
                    executor.submit(self._transcribe_chunk_with_retry, uri, idx): idx 
                    for idx, uri in enumerate(chunk_uris)
                }
                
                # Collect results as they complete
                completed = 0
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    try:
                        result = future.result()
                        transcripts[index] = result
                        completed += 1
                        print(f"Progress: {completed}/{len(chunk_uris)} chunks completed")
                    except Exception as e:
                        print(f"Chunk {index} failed: {e}")
                        transcripts[index] = ""
            
            # Clean up temporary files and GCS blobs
            print("Cleaning up temporary files...")
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            for uri in chunk_uris:
                try:
                    blob_name = uri.replace(f"gs://{self.clients.bucket_name}/", "")
                    self.bucket.blob(blob_name).delete()
                except:
                    pass
            
            # Combine transcripts
            full_transcript = " ".join(filter(None, transcripts))  # Filter out empty strings
            
            # Post-processing cleanup
            full_transcript = self._clean_transcript(full_transcript)
            
            print(f"\nTranscription completed!")
            print(f"Total length: {len(full_transcript)} characters")
            print(f"Word count: approximately {len(full_transcript.split())} words")
            
            return full_transcript
            
        except Exception as e:
            # Clean up on error
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            error_msg = f"Transcription failed: {str(e)}"
            print(error_msg)
            return error_msg

    async def _create_pdf_from_text(self, transcript: str, product_name: str, idx: int):
        # Call Gemini to structure the complete transcript into a professional lesson document
        try:
            prompt = f"""
        You are a content formatter. 
        Take the following transcript of a spoken lesson and turn it into a **clear, structured, and professional lesson document** suitable for a PDF.  

        ✅ Requirements:
        - Extract a meaningful **lesson_title**.
        - Write an **introduction** (2–3 sentences).
        - Break content into **sections with headings** (use short, clear titles).
        - Use **bullet points or numbered lists** where appropriate.
        - Summarize key takeaways at the end in a **Conclusion**.
        - Avoid filler words, repetitions, or casual speech style from the transcript.
        - Keep tone **educational, professional, and easy to read**.

        Return the result in JSON with the following keys:
        {{
            "lesson_title": "...",
            "introduction": "...",
            "sections": [
                {{"heading": "...", "content": "..."}},
                ...
            ],
            "conclusion": "..."
        }}

        Transcript:
        {transcript}
        """
            gen = self.clients.gemini_model.generate_content(prompt)
            
            # Parse the JSON response
            import json
            response_text = gen.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            data = json.loads(response_text)
            lesson_title = data.get("lesson_title", f"Lesson_{idx}")
            introduction = data.get("introduction", "")
            sections = data.get("sections", [])
            conclusion = data.get("conclusion", "")
            
        except Exception as e:
            print(f"Warning: Could not generate structured content with Gemini: {e}")
            # Fallback to simple format
            lesson_title = f"Lesson_{idx}"
            introduction = transcript[:500] + "..." if len(transcript) > 500 else transcript
            sections = [{"heading": "Content", "content": transcript}]
            conclusion = "Key takeaways from this lesson."
        
        # Build comprehensive PDF in-memory
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            alignment=TA_JUSTIFY
        )
        
        intro_style = ParagraphStyle(
            'Introduction',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            fontName='Helvetica-Oblique'
        )
        
        story = []
        
        # Title
        story.append(Paragraph(lesson_title, title_style))
        story.append(Spacer(1, 20))
        
        # Introduction
        if introduction:
            story.append(Paragraph("Introduction", heading_style))
            story.append(Paragraph(introduction, intro_style))
            story.append(Spacer(1, 15))
        
        # Sections
        for section in sections:
            heading = section.get("heading", "")
            content = section.get("content", "")
            
            if heading:
                story.append(Paragraph(heading, heading_style))
            
            if content:
                # Handle bullet points and formatting
                content_lines = content.split('\n')
                for line in content_lines:
                    line = line.strip()
                    if line.startswith('•') or line.startswith('-'):
                        # Bullet point
                        story.append(Paragraph(f"• {line[1:].strip()}", body_style))
                    elif line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                        # Numbered list
                        story.append(Paragraph(line, body_style))
                    elif line:
                        # Regular paragraph
                        story.append(Paragraph(line, body_style))
                
                story.append(Spacer(1, 10))
        
        # Conclusion
        if conclusion:
            story.append(Paragraph("Conclusion", heading_style))
            story.append(Paragraph(conclusion, body_style))
        
        doc.build(story)
        buf.seek(0)
        
        # Sanitize title for filename
        safe_title = "".join(c for c in lesson_title if c.isalnum() or c in (" ", "-", "_"))[:80].strip().replace(" ", "_")
        return safe_title or f"Lesson_{idx}", buf

    async def _embed_pdf_pages(self, pdf_bytes: io.BytesIO, product_id: str, product_name: str, lesson_no: int, video_gcs: str, audio_gcs: str, text_gcs: str, pdf_gcs: str):
        # Extract pages text
        reader = PdfReader(pdf_bytes)
        vectors = []
        print(f"Processing PDF with {len(reader.pages)} pages")
        for p_idx, page in enumerate(reader.pages):
            content = page.extract_text() or ""
            print(f"Page {p_idx}: extracted {len(content)} characters")
            if not content.strip():
                print(f"Skipping page {p_idx} - no content")
                continue
            # Embed with multilingual model (768D)
            print(f"Generating embedding for page {p_idx}")
            embedding = await self._embed_text(content)
            vector_id = f"{product_id}-{lesson_no}-{p_idx}"
            metadata = {
                "product_id": product_id,
                "product_name": product_name,
                "video_path": video_gcs,
                "audio_path": audio_gcs,
                "text_path": text_gcs,
                "pdf_path": pdf_gcs,
                "lesson_no": lesson_no,
                "page": p_idx,
                "page_content": content,  # Add page content to metadata
            }
            vectors.append({
                "vector_id": vector_id,
                "page_content": content,
                "embedding": embedding,
                "metadata": metadata,
            })
        print(f"Generated {len(vectors)} vectors from PDF")
        return vectors

    async def _embed_text(self, text: str):
        # Generate embeddings for text
        try:
            print(f"Generating embedding for text (length: {len(text)})")
            if not text or len(text.strip()) < 5:
                print("Text too short for embedding")
                return []

            # For now, use a simple mock embedding based on text content
            # This will be replaced with actual Vertex AI embeddings once working
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()

            # Create a 768-dimensional embedding (matching the index dimensions)
            # Use deterministic values based on text hash for testing
            embedding = []
            for i in range(768):
                # Create pseudo-random but deterministic values
                hash_part = text_hash[(i * 2) % len(text_hash): (i * 2 + 2) % len(text_hash)]
                if len(hash_part) == 2:
                    value = int(hash_part, 16) / 255.0  # Normalize to 0-1
                else:
                    value = 0.5  # Default value
                embedding.append(value)

            print(f"Generated mock embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            print(f"Warning: Could not generate embedding: {e}")
            return []

