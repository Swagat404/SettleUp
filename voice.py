
import openai
import os
from dotenv import load_dotenv
import re
from openai import OpenAI
from fuzzywuzzy import fuzz, process

# List of names to check for
#names = ["Mubeen", "Uday", "swagat", "anindya", "Aslan","Ayush"]


class Voicee:
    def __init__(self):
        # Set up OpenAI client
        load_dotenv("/Users/swagatbhowmik/CS projects/CodeJam2024/bill_parser/.env")
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=openai.api_key)


    def extract_names(self,sentence, names_list, threshold = 80):
        """
        Extracts names from a sentence based on a list of valid names.

        Args:
            sentence (str): The sentence containing the names.
            names_list (list): The list of names to check for.

        Returns:
            list: A list of names found in the sentence.
        """
        # Convert the sentence to lowercase and split into words
        sentence_words = re.findall(r'\b\w+\b', sentence.lower())
        
        # Extract names that are present in the names_list
    # found_names = [name for name in names_list if name.lower() in sentence_words]
        found_names=[]
        #return found_names
        for word in sentence_words:
            # Find the best match for each word in the sentence
            best_match = process.extractOne(word, names_list, scorer=fuzz.ratio)
            if best_match and best_match[1] >= threshold:  # Match if above the threshold
                found_names.append(best_match[0])

        return list(set(found_names))
    
    def transcribe(self,audio_file,names):

        transcription = self.client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            language="en",  # Specify English language
            response_format="text",  # Get plain text response
            prompt="The following audio is in English with possible accent variations."  # Help guide the model
        )
        print("Transcribed text:", transcription)
        # Extract names from the transcribed text
        found_names = self.extract_names(transcription, names, threshold=80)
        return found_names

