import vosk
import json
import pyaudio
import sys
import os
import subprocess
import windows_system

# Set up Vosk model
model_path = "vosk-model-small-en-us-0.15"

# Check if model exists
if not os.path.exists(model_path):
    print(f"Model not found at {model_path}")
    sys.exit(1)

# Load the model
print("Loading Vosk model...")
try:
    model = vosk.Model(model_path)
except Exception as e:
    print(f"Error loading Vosk model: {e}")
    sys.exit(1)

# TTS function using Windows SAPI via PowerShell
def speak(text):
    """Speak text using Windows built-in speech synthesis"""
    try:
        # Escape single quotes for PowerShell
        escaped_text = text.replace("'", "''")
        cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.SelectVoiceByHints(\'Female\'); $speak.Rate = 0; $speak.Speak(\'{escaped_text}\')"'
        subprocess.run(cmd, shell=True)
    except Exception as e:
        print(f"Error in text-to-speech: {e}")

# Set up PyAudio
try:
    mic = pyaudio.PyAudio()
    stream = mic.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000
    )
    stream.start_stream()
except Exception as e:
    print(f"Error setting up microphone: {e}")
    sys.exit(1)

# Create Vosk recognizer
rec = vosk.KaldiRecognizer(model, 16000)

# Confirmation helper function
def get_confirmation(prompt):
    """
    Ask user for yes/no confirmation
    Returns True if yes, False if no
    """
    try:
        # Ask the question
        speak(prompt)
        
        print(f"SYDNY: {prompt}")
        print("Waiting for yes or no...")
        
        # Listen for response
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                
                if text:
                    print(f"You said: {text}")
                    
                    # Check for yes
                    if "yes" in text or "yeah" in text or "confirm" in text:
                        return True
                    
                    # Check for no
                    if "no" in text or "cancel" in text or "nope" in text:
                        return False
                    
                    # Didn't understand, ask again
                    speak("Please say yes or no")
    except Exception as e:
        print(f"Error in confirmation: {e}")
        return False

def parse_command(text):
    """
    Parse natural language command into intent and target
    Returns: (intent, target) or (None, None) if no command found
    """
    try:
        # List of filler words to ignore
        filler_words = [
            "please", "could", "you", "can", "would", "will",
            "up", "the", "a", "an", "for", "me", "my"
        ]
        
        # Split into words and convert to lowercase
        words = text.lower().split()
        
        # Remove filler words
        cleaned_words = [w for w in words if w not in filler_words]
        
        # Check for "open file" command FIRST (before general "open")
        if "file" in cleaned_words and "open" in cleaned_words:
            cleaned_words = [w for w in cleaned_words if w not in ["open", "file"]]
            if cleaned_words:
                target = " ".join(cleaned_words)
                return ("openfile", target)
        
        # Check for "open" command (for apps)
        if "open" in cleaned_words:
            cleaned_words.remove("open")
            if cleaned_words:
                target = " ".join(cleaned_words)
                return ("open", target)
        
        # Check for "close" command
        if "close" in cleaned_words:
            cleaned_words.remove("close")
            if cleaned_words:
                target = " ".join(cleaned_words)
                return ("close", target)
        
        # Check for "search" or "find" command
        if "search" in cleaned_words or "find" in cleaned_words:
            # Remove both search/find and "file" if present
            cleaned_words = [w for w in cleaned_words if w not in ["search", "find", "file"]]
            if cleaned_words:
                target = " ".join(cleaned_words)
                return ("search", target)
        
        # Check for "delete" command
        if "delete" in cleaned_words:
            cleaned_words = [w for w in cleaned_words if w not in ["delete", "file"]]
            if cleaned_words:
                target = " ".join(cleaned_words)
                return ("delete", target)
        
        # Check for "volume" commands
        if "volume" in cleaned_words:
            cleaned_words.remove("volume")
            # Look for a number
            for word in cleaned_words:
                if word.isdigit():
                    return ("volume", word)
            return ("volume", None)
        
        if "mute" in cleaned_words:
            return ("mute", None)
        
        if "unmute" in cleaned_words:
            return ("unmute", None)
        
        # Check for power commands
        if "shutdown" in cleaned_words or "shut" in cleaned_words:
            return ("shutdown", None)
        
        if "restart" in cleaned_words:
            return ("restart", None)
        
        if "sleep" in cleaned_words:
            return ("sleep", None)
        
        if "exit" in cleaned_words or "quit" in cleaned_words:
            return ("exit", None)
        
        # No command found
        return (None, None)
    
    except Exception as e:
        print(f"Error parsing command: {e}")
        return (None, None)

# Introduction
print("SYDNY starting...")
speak("My name is Sydney, how's it going?")

# Main voice loop
print("\nListening...")
while True:
    try:
        # Read audio data from microphone
        data = stream.read(4000, exception_on_overflow=False)
        
        # Feed audio to Vosk
        if rec.AcceptWaveform(data):
            # Vosk recognized a complete phrase
            result = json.loads(rec.Result())
            text = result.get("text", "")
            
            if text:  # Only process if we got actual text
                print(f"You said: {text}")
                
                # Parse the command using our smart parser
                intent, target = parse_command(text)
                
                # Handle exit command
                if intent == "exit":
                    speak("Goodbye")
                    break
                
                # Handle volume commands
                elif intent == "volume":
                    if target:
                        try:
                            level = int(target)
                            # Validate range (0-100)
                            if 0 <= level <= 100:
                                result = windows_system.set_volume(level)
                                speak(result)
                            else:
                                speak("Volume must be between 0 and 100")
                        except ValueError:
                            speak("Please specify a valid number for volume")
                    else:
                        speak("Please specify a volume level")
                
                elif intent == "mute":
                    try:
                        result = windows_system.mute()
                        speak(result)
                    except Exception as e:
                        speak("Error muting audio")
                        print(f"Mute error: {e}")
                
                elif intent == "unmute":
                    try:
                        result = windows_system.unmute()
                        speak(result)
                    except Exception as e:
                        speak("Error unmuting audio")
                        print(f"Unmute error: {e}")
                
                # Handle power commands (with confirmation)
                elif intent == "shutdown":
                    try:
                        if get_confirmation("Are you sure you want to shut down?"):
                            result = windows_system.shutdown_system()
                            speak(result)
                        else:
                            speak("Shutdown cancelled")
                    except Exception as e:
                        speak("Error with shutdown command")
                        print(f"Shutdown error: {e}")
                
                elif intent == "restart":
                    try:
                        if get_confirmation("Are you sure you want to restart?"):
                            result = windows_system.restart_system()
                            speak(result)
                        else:
                            speak("Restart cancelled")
                    except Exception as e:
                        speak("Error with restart command")
                        print(f"Restart error: {e}")
                
                elif intent == "sleep":
                    try:
                        if get_confirmation("Are you sure you want to sleep?"):
                            result = windows_system.sleep_system()
                            speak(result)
                        else:
                            speak("Sleep cancelled")
                    except Exception as e:
                        speak("Error with sleep command")
                        print(f"Sleep error: {e}")
                
                # Handle app commands
                elif intent == "open":
                    if target:
                        try:
                            result = windows_system.open_app(target)
                            speak(result)
                        except Exception as e:
                            speak(f"Error opening {target}")
                            print(f"Open app error: {e}")
                    else:
                        speak("What would you like me to open?")
                
                elif intent == "close":
                    if target:
                        try:
                            result = windows_system.close_app(target)
                            speak(result)
                        except Exception as e:
                            speak(f"Error closing {target}")
                            print(f"Close app error: {e}")
                    else:
                        speak("What would you like me to close?")
                
                # Handle file operations
                elif intent == "search":
                    if target:
                        try:
                            matches = windows_system.search_file(target)
                            if matches:
                                speak(f"Found {len(matches)} files")
                                for match in matches:
                                    print(f"  - {match}")
                            else:
                                speak(f"No files found matching {target}")
                        except Exception as e:
                            speak("Error searching for file")
                            print(f"Search error: {e}")
                    else:
                        speak("What file would you like me to search for?")
                
                elif intent == "delete":
                    if target:
                        try:
                            matches = windows_system.search_file(target)
                            if matches:
                                if get_confirmation(f"Are you sure you want to delete {target}?"):
                                    result = windows_system.delete_file(matches[0])
                                    speak(result)
                                else:
                                    speak("Delete cancelled")
                            else:
                                speak(f"Could not find file {target}")
                        except Exception as e:
                            speak("Error deleting file")
                            print(f"Delete error: {e}")
                    else:
                        speak("What file would you like me to delete?")
                
                elif intent == "openfile":
                    if target:
                        try:
                            matches = windows_system.search_file(target)
                            if matches:
                                result = windows_system.open_file(matches[0])
                                speak(result)
                            else:
                                speak(f"Could not find file {target}")
                        except Exception as e:
                            speak("Error opening file")
                            print(f"Open file error: {e}")
                    else:
                        speak("What file would you like me to open?")
                
                # Handle unknown commands
                elif intent is None:
                    speak(f"You said {text}, sir")
                
                print("\nListening...")
                
    except KeyboardInterrupt:
        print("\nStopping...")
        speak("Shutting down")
        break
    except Exception as e:
        print(f"Error in main loop: {e}")
        # Don't break, just continue listening
        continue

# Cleanup
try:
    stream.stop_stream()
    stream.close()
    mic.terminate()
    print("Audio resources cleaned up")
except Exception as e:
    print(f"Error during cleanup: {e}")