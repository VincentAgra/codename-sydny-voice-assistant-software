"""
SYDNY - Integrated Voice + GUI System
Combines voice recognition, TTS, and HAL-inspired GUI with FULL command support
"""

import sys
import os
import json
import threading
from queue import Queue

# PyQt5 imports
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont

# Voice imports
import vosk
import pyaudio
import subprocess
import windows_system


# ============================================================================
# SIGNAL EMITTER (for thread-safe GUI updates)
# ============================================================================

class Signals(QObject):
    """Signals for communicating between voice thread and GUI"""
    update_status = pyqtSignal(str)  # Update status text
    add_terminal_message = pyqtSignal(str)  # Add message to terminal
    set_listening = pyqtSignal(bool)  # Set listening state
    set_speaking = pyqtSignal(bool)  # Set speaking state
    show_confirmation = pyqtSignal(str)  # Show confirm/cancel buttons
    hide_confirmation = pyqtSignal()  # Hide confirm/cancel buttons
    close_window = pyqtSignal()  # Close the GUI window


# ============================================================================
# EYE WIDGET
# ============================================================================

class EyeWidget(QWidget):
    """The HAL 9000 red eye"""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(500, 500)
        self.glow_intensity = 0.5
        self.is_speaking = False
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_glow)
        self.timer.start(50)
        
        self.glow_direction = 1
    
    def animate_glow(self):
        if self.is_speaking:
            self.glow_intensity += 0.05 * self.glow_direction
            if self.glow_intensity >= 1.0:
                self.glow_direction = -1
            elif self.glow_intensity <= 0.3:
                self.glow_direction = 1
        else:
            self.glow_intensity = 0.5
        self.update()
    
    def set_speaking(self, speaking):
        self.is_speaking = speaking
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        center = QPoint(center_x, center_y)
        
        ring_radius = 180
        painter.setPen(QPen(QColor(150, 150, 150), 14))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, ring_radius, ring_radius)
        
        gradient = QRadialGradient(center, ring_radius - 20)
        intensity = int(255 * self.glow_intensity)
        gradient.setColorAt(0, QColor(255, intensity, 0, 255))
        gradient.setColorAt(0.3, QColor(255, 0, 0, 200))
        gradient.setColorAt(0.7, QColor(150, 0, 0, 150))
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, ring_radius - 20, ring_radius - 20)
        
        core_size = int(25 * self.glow_intensity)
        painter.setBrush(QColor(255, 255, 200, 200))
        painter.drawEllipse(center, core_size, core_size)


# ============================================================================
# TERMINAL DISPLAY WIDGET
# ============================================================================

class TerminalWidget(QTextEdit):
    """Terminal-style scrolling display for conversation"""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(300)
        self.setMaximumHeight(400)
        self.setMinimumWidth(500)
        self.setMaximumWidth(600)
        
        # Make it read-only
        self.setReadOnly(True)
        
        # Set terminal styling
        self.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #00ff00;
                border: 1px solid #646464;
                font-family: 'Courier';
                font-size: 10pt;
                padding: 10px;
            }
        """)
        
        # Set font
        font = QFont("Courier", 10)
        self.setFont(font)
    
    def add_message(self, message):
        """Add a message to the terminal and auto-scroll"""
        self.append(message)
        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear(self):
        """Clear all messages"""
        self.clear()


# ============================================================================
# MAIN GUI
# ============================================================================

class SydnyGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.signals = Signals()
        
        self.signals.update_status.connect(self.update_status)
        self.signals.add_terminal_message.connect(self.add_terminal_message)
        self.signals.set_listening.connect(self.set_listening)
        self.signals.set_speaking.connect(self.set_speaking)
        self.signals.show_confirmation.connect(self.show_confirmation)
        self.signals.hide_confirmation.connect(self.hide_confirmation)
        self.signals.close_window.connect(self.close)  # Close the window
        
        self.confirmation_response = Queue()
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        
        self.setWindowTitle("SYDNY")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #000000;")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(50, 50, 50, 50)
        
        layout.addStretch(1)
        
        # Eye
        self.eye = EyeWidget()
        layout.addWidget(self.eye, alignment=Qt.AlignCenter)
        
        # Status text
        self.status_label = QLabel("SYDNY")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Courier", 24, QFont.Bold))
        self.status_label.setStyleSheet("color: #888888; letter-spacing: 10px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch(1)
        
        # Terminal display (centered)
        self.terminal = TerminalWidget()
        layout.addWidget(self.terminal, alignment=Qt.AlignCenter)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.addStretch()
        
        self.confirm_button = QPushButton("CONFIRM")
        self.confirm_button.setFont(QFont("Courier", 12, QFont.Bold))
        self.confirm_button.setMinimumSize(120, 40)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #00ff00;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #00ff00;
                color: #000000;
            }
        """)
        self.confirm_button.clicked.connect(self.on_confirm)
        self.confirm_button.hide()
        button_layout.addWidget(self.confirm_button)
        
        self.cancel_button = QPushButton("CANCEL")
        self.cancel_button.setFont(QFont("Courier", 12, QFont.Bold))
        self.cancel_button.setMinimumSize(120, 40)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ff0000;
                border: 2px solid #ff0000;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #ff0000;
                color: #000000;
            }
        """)
        self.cancel_button.clicked.connect(self.on_cancel)
        self.cancel_button.hide()
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        layout.addSpacing(20)
        
        central_widget.setLayout(layout)
    
    def update_status(self, text):
        """Update status label"""
        self.status_label.setText(text)
    
    def set_listening(self, listening):
        """Set listening state"""
        if listening:
            self.status_label.setText("LISTENING")
            self.add_terminal_message("> Listening...")
    
    def add_terminal_message(self, message):
        """Add message to terminal display"""
        self.terminal.add_message(message)
    
    def set_speaking(self, speaking):
        """Set speaking state"""
        self.eye.set_speaking(speaking)
        if speaking:
            self.status_label.setText("SPEAKING")
        else:
            self.status_label.setText("SYDNY")
    
    def show_confirmation(self, prompt):
        """Show confirmation buttons"""
        self.status_label.setText(prompt)
        self.confirm_button.show()
        self.cancel_button.show()
    
    def hide_confirmation(self):
        """Hide confirmation buttons"""
        self.confirm_button.hide()
        self.cancel_button.hide()
    
    def on_confirm(self):
        """User clicked confirm"""
        self.confirmation_response.put(True)
        self.hide_confirmation()
    
    def on_cancel(self):
        """User clicked cancel"""
        self.confirmation_response.put(False)
        self.hide_confirmation()


# ============================================================================
# VOICE SYSTEM (runs in separate thread)
# ============================================================================

class VoiceSystem:
    """Voice recognition and TTS system"""
    
    def __init__(self, gui_signals, confirmation_queue):
        self.signals = gui_signals
        self.confirmation_queue = confirmation_queue
        
        # Set up Vosk model
        model_path = "vosk-model-small-en-us-0.15"
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}")
            sys.exit(1)
        
        print("Loading Vosk model...")
        try:
            self.model = vosk.Model(model_path)
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            sys.exit(1)
        
        # Set up PyAudio
        try:
            self.mic = pyaudio.PyAudio()
            self.stream = self.mic.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8000
            )
            self.stream.start_stream()
        except Exception as e:
            print(f"Error setting up microphone: {e}")
            sys.exit(1)
        
        # Create Vosk recognizer
        self.rec = vosk.KaldiRecognizer(self.model, 16000)
        
        self.running = True
    
    def speak(self, text):
        """Speak text using Windows SAPI"""
        self.signals.set_speaking.emit(True)
        self.signals.add_terminal_message.emit(f"> SYDNY: {text}")
        
        try:
            escaped_text = text.replace("'", "''")
            cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.SelectVoiceByHints(\'Female\'); $speak.Rate = 0; $speak.Speak(\'{escaped_text}\')"'
            subprocess.run(cmd, shell=True)
        except Exception as e:
            print(f"Error in TTS: {e}")
        
        self.signals.set_speaking.emit(False)
    
    def get_confirmation_gui(self, prompt):
        """Get confirmation from GUI buttons"""
        self.signals.show_confirmation.emit(prompt)
        response = self.confirmation_queue.get()
        self.signals.hide_confirmation.emit()
        return response
    
    def parse_command(self, text):
        """
        Parse natural language command into intent and target
        Returns: (intent, target) or (None, None) if no command found
        """
        try:
            filler_words = [
                "please", "could", "you", "can", "would", "will",
                "up", "the", "a", "an", "for", "me", "my"
            ]
            
            words = text.lower().split()
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
            
            return (None, None)
        
        except Exception as e:
            print(f"Error parsing command: {e}")
            return (None, None)
    
    def run(self):
        """Main voice loop with FULL command handling"""
        print("SYDNY starting...")
        self.speak("My name is Sydney, how's it going?")
        
        print("\nListening...")
        self.signals.set_listening.emit(True)
        
        while self.running:
            try:
                data = self.stream.read(4000, exception_on_overflow=False)
                
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get("text", "")
                    
                    if text:
                        print(f"You said: {text}")
                        self.signals.add_terminal_message.emit(f"> You: {text}")
                        self.signals.set_listening.emit(False)
                        
                        # Parse the command using our smart parser
                        intent, target = self.parse_command(text)
                        
                        # Handle exit command
                        if intent == "exit":
                            self.speak("Goodbye")
                            self.running = False
                            self.signals.close_window.emit()  # Close the GUI
                            break
                        
                        # Handle volume commands
                        elif intent == "volume":
                            if target:
                                try:
                                    level = int(target)
                                    if 0 <= level <= 100:
                                        result = windows_system.set_volume(level)
                                        self.speak(result)
                                    else:
                                        self.speak("Volume must be between 0 and 100")
                                except ValueError:
                                    self.speak("Please specify a valid number for volume")
                            else:
                                self.speak("Please specify a volume level")
                        
                        elif intent == "mute":
                            try:
                                result = windows_system.mute()
                                self.speak(result)
                            except Exception as e:
                                self.speak("Error muting audio")
                                print(f"Mute error: {e}")
                        
                        elif intent == "unmute":
                            try:
                                result = windows_system.unmute()
                                self.speak(result)
                            except Exception as e:
                                self.speak("Error unmuting audio")
                                print(f"Unmute error: {e}")
                        
                        # Handle power commands (with confirmation)
                        elif intent == "shutdown":
                            try:
                                if self.get_confirmation_gui("Confirm shutdown?"):
                                    result = windows_system.shutdown_system()
                                    self.speak(result)
                                else:
                                    self.speak("Shutdown cancelled")
                            except Exception as e:
                                self.speak("Error with shutdown command")
                                print(f"Shutdown error: {e}")
                        
                        elif intent == "restart":
                            try:
                                if self.get_confirmation_gui("Confirm restart?"):
                                    result = windows_system.restart_system()
                                    self.speak(result)
                                else:
                                    self.speak("Restart cancelled")
                            except Exception as e:
                                self.speak("Error with restart command")
                                print(f"Restart error: {e}")
                        
                        elif intent == "sleep":
                            try:
                                if self.get_confirmation_gui("Confirm sleep?"):
                                    result = windows_system.sleep_system()
                                    self.speak(result)
                                else:
                                    self.speak("Sleep cancelled")
                            except Exception as e:
                                self.speak("Error with sleep command")
                                print(f"Sleep error: {e}")
                        
                        # Handle app commands
                        elif intent == "open":
                            if target:
                                try:
                                    result = windows_system.open_app(target)
                                    self.speak(result)
                                except Exception as e:
                                    self.speak(f"Error opening {target}")
                                    print(f"Open app error: {e}")
                            else:
                                self.speak("What would you like me to open?")
                        
                        elif intent == "close":
                            if target:
                                try:
                                    result = windows_system.close_app(target)
                                    self.speak(result)
                                except Exception as e:
                                    self.speak(f"Error closing {target}")
                                    print(f"Close app error: {e}")
                            else:
                                self.speak("What would you like me to close?")
                        
                        # Handle file operations
                        elif intent == "search":
                            if target:
                                try:
                                    matches = windows_system.search_file(target)
                                    if matches:
                                        self.speak(f"Found {len(matches)} files")
                                        for match in matches:
                                            print(f"  - {match}")
                                            self.signals.add_terminal_message.emit(f"  - {match}")
                                    else:
                                        self.speak(f"No files found matching {target}")
                                except Exception as e:
                                    self.speak("Error searching for file")
                                    print(f"Search error: {e}")
                            else:
                                self.speak("What file would you like me to search for?")
                        
                        elif intent == "delete":
                            if target:
                                try:
                                    matches = windows_system.search_file(target)
                                    if matches:
                                        if self.get_confirmation_gui(f"Delete {target}?"):
                                            result = windows_system.delete_file(matches[0])
                                            self.speak(result)
                                        else:
                                            self.speak("Delete cancelled")
                                    else:
                                        self.speak(f"Could not find file {target}")
                                except Exception as e:
                                    self.speak("Error deleting file")
                                    print(f"Delete error: {e}")
                            else:
                                self.speak("What file would you like me to delete?")
                        
                        elif intent == "openfile":
                            if target:
                                try:
                                    matches = windows_system.search_file(target)
                                    if matches:
                                        result = windows_system.open_file(matches[0])
                                        self.speak(result)
                                    else:
                                        self.speak(f"Could not find file {target}")
                                except Exception as e:
                                    self.speak("Error opening file")
                                    print(f"Open file error: {e}")
                            else:
                                self.speak("What file would you like me to open?")
                        
                        # Handle unknown commands
                        elif intent is None:
                            self.speak(f"You said {text}, sir")
                        
                        print("\nListening...")
                        self.signals.set_listening.emit(True)
            
            except KeyboardInterrupt:
                print("\nStopping...")
                self.speak("Shutting down")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                continue
        
        # Cleanup
        try:
            self.stream.stop_stream()
            self.stream.close()
            self.mic.terminate()
            print("Audio resources cleaned up")
        except Exception as e:
            print(f"Error during cleanup: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    app = QApplication(sys.argv)
    
    # Create GUI
    window = SydnyGUI()
    window.show()
    
    # Create voice system
    voice_system = VoiceSystem(window.signals, window.confirmation_response)
    
    # Start voice system in separate thread
    voice_thread = threading.Thread(target=voice_system.run, daemon=True)
    voice_thread.start()
    
    # Run GUI
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()