import sys
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import ollama_service

class OllamaStartTests(unittest.TestCase):
    def test_already_running(self):
        with patch.object(ollama_service,'running',return_value=True), patch.object(ollama_service.subprocess,'Popen') as popen:
            self.assertEqual(ollama_service.start()[0],'already_running')
            popen.assert_not_called()
    def test_missing_executable(self):
        with patch.object(ollama_service,'running',return_value=False), patch.object(ollama_service.shutil,'which',return_value=None):
            self.assertEqual(ollama_service.start()[0],'missing')
    def test_successful_start(self):
        with patch.object(ollama_service,'running',side_effect=[False,True]), patch.object(ollama_service.shutil,'which',return_value='/usr/bin/ollama'), patch.object(ollama_service.subprocess,'Popen',return_value=Mock()) as popen:
            self.assertEqual(ollama_service.start()[0],'started')
            self.assertEqual(popen.call_args.args[0],['/usr/bin/ollama','serve'])
    def test_executable_error(self):
        with patch.object(ollama_service,'running',return_value=False), patch.object(ollama_service.shutil,'which',return_value='/usr/bin/ollama'), patch.object(ollama_service.subprocess,'Popen',side_effect=OSError('hiba')):
            self.assertEqual(ollama_service.start()[0],'failed')
