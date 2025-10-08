import requests
import logging
import time
import random
import json
import pyzstd

from client import SAMPLE_URL

#API_GATEWAY_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_retrieve/notes"  # Update with your actual endpoint
#RETRIEVE_NOTE_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_retrieve/retrieve"  # Update with your actual endpoint for retrieval

SAMPLE_URLS = ["https://www.gutenberg.org/files/1342/1342-0.txt",
               "https://www.gutenberg.org/files/2701/2701-0.txt",
               "https://www.gutenberg.org/files/84/84-0.txt",
               "https://www.gutenberg.org/files/100/100-0.txt",
               "https://www.gutenberg.org/files/2641/2641-0.txt",
               "https://www.gutenberg.org/files/37106/37106-0.txt",
               "https://www.gutenberg.org/files/98/98-0.txt",
               "https://www.gutenberg.org/files/1400/1400-0.txt",
               "https://www.gutenberg.org/files/768/768-0.txt",
               "https://www.gutenberg.org/files/2554/2554-0.txt"]

# Set up logging for Lambda/CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,filename="training.log",encoding='utf-8')

filepath = "/Users/nikhilniranjan/andromeda/training-files/"
data_files_count = 10
training_set_count = 10000
training_note_size = 500
sample_text = []
samples = []

# Download sample text
for i in range(len(SAMPLE_URLS)):
    response = requests.get(SAMPLE_URLS[i])
    sample_text.append(response.text)
    print(len(sample_text[i]))
    
for i in range(training_set_count):
    note_length = random.randint(100, training_note_size)
    #vary start point randomly
    which_file = random.randint(0, data_files_count - 1)
    start_point = random.randint(0, len(sample_text[which_file]) - note_length)
    content = sample_text[which_file][start_point:start_point + note_length]
    samples.append(b"content")

    #filename = f"{filepath}{str(i)}.txt"
    #with open(filename, "w", encoding="utf-8") as f:
        #f.write(content)
        
    dictionary_data = pyzstd.train_dict(samples, dict_size = 1024)
    
    with open(f"{filepath}zstd_dictionary_110kB", "wb") as f:
        f.write(dictionary_data)
        
        


        
        
