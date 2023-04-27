from flask import Flask, request, jsonify
from transformers import PegasusTokenizer, PegasusForConditionalGeneration
import os
from flask_cors import CORS
import re

os.environ['PYTHONHTTPSVERIFY'] = '0'

app = Flask(__name__, static_folder='../public')
CORS(app, origins='http://localhost:5173')

def length_parameters(summary_length_choice):
    summary_length_factors = {
        "short": (0.15, 0.2),
        "medium": (0.3, 0.4),
        "long": (0.6, 0.7)
    }
    
    return summary_length_factors[summary_length_choice]

def split_into_sentences(text):
    sentences = re.findall('[A-Z][^\.!?]*[\.!?]', text)
    sentence_tokens = []

    for sentence in sentences:
        tokenized_sentence = tokenizer(sentence)
        sentence_tokens.append(len(tokenized_sentence['input_ids']))

    max_token_length = 512
    current_token_length = sentence_tokens[0]
    current_sentence = sentences[0]
    result = []
    for sentence_token, sentence in zip(sentence_tokens[1:], sentences[1:]):
        if current_token_length + sentence_token < max_token_length:
            current_token_length += sentence_token
            current_sentence += ' ' + sentence
        else:
            result.append((current_sentence, len(tokenizer(current_sentence)['input_ids'])))
            current_token_length = sentence_token
            current_sentence = sentence
    
    result.append((current_sentence, len(tokenizer(current_sentence)['input_ids'])))

    return result

@app.route('/')
def index():
  return app.send_static_file('index.html')

model_name = "google/pegasus-xsum"
tokenizer = PegasusTokenizer.from_pretrained(model_name)
model = PegasusForConditionalGeneration.from_pretrained(model_name)

@app.route('/', methods=['POST'])
def summarize():
    request_data = request.get_json()
    input_text = request_data['text']
    max_summary_length = request_data['length']
  
    input_list = split_into_sentences(input_text.replace('\n',''))
    stitch = []

    length_factors = length_parameters(max_summary_length)

    for grouped_sentence, grouped_sentence_length in input_list:
        inputs = tokenizer(grouped_sentence, return_tensors='pt')

        summary_ids = model.generate(inputs['input_ids'], max_length=int(length_factors[1]*grouped_sentence_length), min_length=int(length_factors[0]*grouped_sentence_length), no_repeat_ngram_size=4)
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        complete_sentences = re.findall('[A-Z][^\.!?]*[\.!?]', summary)
        complete_summary = " ".join(complete_sentences)
        stitch.append(complete_summary)

    #print(" ".join(stitch))
    return jsonify({'summary':summary})

# def summarize():
#   request_data = request.get_json()
#   input_text = request_data['text']
#   max_summary_length = request_data['length']
    
#   inputs = tokenizer(input_text, return_tensors='pt')

#   summary_ids = model.generate(inputs['input_ids'], max_length=max_summary_length, min_length=56, early_stopping=True)
#   summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

#   return jsonify({'summary': summary})

if __name__ == "__main__":
  app.run()