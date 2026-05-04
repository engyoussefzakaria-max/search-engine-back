import fitz
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import _get_punkt_tokenizer, word_tokenize
from nltk.stem import PorterStemmer
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
# Ensure NLTK resources are available
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)  # <-- Add this line!
nltk.download('stopwords', quiet=True)
# --------------------------
def extract_text_from_pdf_stream(pdf_file, filename="document"):
    """
    Takes a PDF file object (not a path) and extracts text per page.
    """
    # Read the file-like object into bytes
    pdf_bytes = pdf_file.read()
    
    # Open the PDF using the byte stream
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    documents = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        
        # هنتأكد ان الصفحة مش فاضية
        if text.strip():
            doc_id = f"{filename}_page_{page_num + 1}"
            documents.append({
                "doc_id": doc_id,
                "original_text": text.strip()
            })
            
    return documents

def clean_and_tokenize(text):
    """
    Applies lowercasing, regex filtering, stopword removal, and stemming.
    """
    # تحويل الحروف small  
    text = text.lower()
    
    # remove numbers and punctuation (keeps only a-z and whitespace)
    text = re.sub(r'[^a-z\s]', '', text)
    
    # tokenization
    tokens = word_tokenize(text)
    
    # stopwords filtering
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [word for word in tokens if word not in stop_words]
    
    # stemming
    stemmer = PorterStemmer()
    stemmed_tokens = [stemmer.stem(word) for word in filtered_tokens]

    return stemmed_tokens

_treebank_word_tokenizer = nltk.NLTKWordTokenizer()

def word_tokenize(text, language="english", preserve_line=False):
    """
    Return a tokenized copy of *text*,
    using NLTK's recommended word tokenizer
    (currently an improved :class:`.TreebankWordTokenizer`
    along with :class:`.PunktSentenceTokenizer`
    for the specified language).

    :param text: text to split into words
    :type text: str
    :param language: the model name in the Punkt corpus
    :type language: str
    :param preserve_line: A flag to decide whether to sentence tokenize the text or not.
    :type preserve_line: bool
    """
    sentences = [text] if preserve_line else sent_tokenize(text, language)
    return [
        token for sent in sentences for token in _treebank_word_tokenizer.tokenize(sent)
    ]

# Standard sentence tokenizer.
def sent_tokenize(text, language="english"):
    """
    Return a sentence-tokenized copy of *text*,
    using NLTK's recommended sentence tokenizer
    (currently :class:`.PunktSentenceTokenizer`
    for the specified language).

    :param text: text to split into sentences
    :param language: the model name in the Punkt corpus
    """
    tokenizer = _get_punkt_tokenizer(language)
    return tokenizer.tokenize(text)

def pdf_processing_pipeline(pdf_file, filename="document"):
    """
    The main pipeline: Takes a PDF file object, extracts text, 
    cleans it, and returns a list of dictionaries with clean tokens.
    """
    # Step 1: Extract text
    raw_documents = extract_text_from_pdf_stream(pdf_file, filename)
    
    processed_documents = []
    
    # Step 2: Tokenize and clean each page
    for doc in raw_documents:
        tokens = clean_and_tokenize(doc["original_text"])
        
        # Only add to results if tokens exist after cleaning
        if tokens:
            processed_documents.append({
                "original_text": doc["original_text"],
                "tokens": tokens
            })
            
    return processed_documents