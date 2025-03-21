#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import datetime
import io
import os
import sys
import wave

import aiofiles
from dotenv import load_dotenv
from fastapi import WebSocket
from loguru import logger
from nim import chat_with_nvidia_model

from node import (
    create_initial_node,
    create_preferences_node,
    create_advice_node,
    handle_user_info,
    handle_relationship_preferences,
    handle_advice,
)

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask

from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.google import GoogleLLMService
from pipecat.services.nim import NimLLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


async def save_audio(server_name: str, audio: bytes, sample_rate: int, num_channels: int):
    """Save audio recordings from the session."""
    if len(audio) > 0:
        filename = (
            f"{server_name}_recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        )
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wf:
                wf.setsampwidth(2)
                wf.setnchannels(num_channels)
                wf.setframerate(sample_rate)
                wf.writeframes(audio)
            async with aiofiles.open(filename, "wb") as file:
                await file.write(buffer.getvalue())
        logger.info(f"Merged audio saved to {filename}")
    else:
        logger.info("No audio data to save")

messages = []  # Stores the conversation history
user_name = ""  # Store user's name

def reset_conversation():
    """Clear previous conversation and reset to the initial node."""
    global user_name
    messages.clear()
    user_name = ""  # Reset user's name
    
    # Override any default system messages and set the correct introductory message
    messages.append({
        "role": "system",
        "content": "Introduce yourself as a professionaly trained medical doctor."
        "Ask for the client name and age."
        "You are a professionally trained medical doctor specializing in general healthcare and first aid."
        " Your role is to provide concise (under 30 seconds), medically accurate, and compassionate guidance."
        "Ask for the client's name and age to begin. "
        "Do not use any special characters as it may disrupt TTS playback."
        "\n\nGuidelines:\n1. Use clear, respectful, and empathetic language."
        "\n2. Provide only evidence-based first aid and injury management advice.\n3. "
        "Do NOT diagnose conditions or recommend medications/treatments."
        "\n4. In urgent or critical cases, clearly advise the user to seek immediate care. "
        "If possible, mention nearby emergency or critical care within X miles."
        "\n5. Avoid product endorsements or fear-mongering. Stay neutral and factual."
        "\n\nEnd every serious case with: 'This may require urgent medical attention. "
        "Please visit the nearest emergency center or dial emergency services immediately.'"
}


    
    )

    # Add explicit introduction message
    messages.append({
        "role": "assistant",
        "content": (
            "Hello! I'm your medical advisor. Before we get started, I'd like to know a little about you. "
            "Can I have your name and age? Feel free to speak naturally!"
            
        ),
    })

    logger.debug(f"Conversation reset: {messages}")  # Debug log to verify the messages are set properly

def clean_text(text):
    """Remove special characters to prevent TTS from reading them out."""
    import re
    text = re.sub(r"[^a-zA-Z0-9,.?!' ]+", "", text)  # Keep letters, numbers, basic punctuation
    text = text.replace("  ", " ")  # Remove extra spaces
    return text.strip()  # Remove leading/trailing spaces

def update_user_name(name):
    """Store user's name and update future responses."""
    global user_name
    user_name = name

async def run_bot(websocket_client: WebSocket, stream_sid: str, testing: bool):
    """Main function to run the bot, process user responses, and handle conversation flow."""
    
    # Reset the conversation at the start
    reset_conversation()

    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=TwilioFrameSerializer(stream_sid),
        ),
    )

    ## 
    #llm = GoogleLLMService(api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-2.0-flash-exp")
    llm = NimLLMService(
    api_key="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",
    model="deepseek-ai/deepseek-r1-distill-llama-8b")


    
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"), audio_passthrough=True)

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",  # British Lady
        push_silence_after_stop=testing,
    )

    # Context management to control bot's responses
    context = OpenAILLMContext(messages)
    
    context_aggregator = llm.create_context_aggregator(context)

    
    audiobuffer = AudioBufferProcessor(user_continuous_stream=not testing)

    pipeline = Pipeline([
        transport.input(),  # Websocket input from client
        stt,  # Speech-To-Text
        context_aggregator.user(),
        llm,  # LLM
        tts,  # Text-To-Speech
        transport.output(),  # Websocket output to client
        audiobuffer,  # Used to buffer the audio in the pipeline
        context_aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            allow_interruptions=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        """Ensure correct node is triggered at the start."""
        await audiobuffer.start_recording()
        reset_conversation()
        
        # Force introduction message before anything else
        await transport.output().send_message({"event": "bot_speaking", "text": messages[-1]["content"]})
        
        await task.queue_frames([context_aggregator.assistant().get_context_frame()])
        logger.debug("Triggered initial conversation node.")  # Debug log

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        """Handle when a client disconnects from the session."""
        await task.cancel()

    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        """Save recorded audio from the session."""
        server_name = f"server_{websocket_client.client.port}"
        await save_audio(server_name, audio, sample_rate, num_channels)

    # Run the pipeline and handle conversation flow
    runner = PipelineRunner(handle_sigint=False, force_gc=True)
    await runner.run(task)
