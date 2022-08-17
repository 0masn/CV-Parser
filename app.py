import regex as re
import pdfminer
from io import StringIO
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

import docx2txt
import os
import urllib.request
from flask import Flask, request, redirect, jsonify
from werkzeug.utils import secure_filename
app = Flask(__name__)
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def open_pdf_file(infile):
    output = StringIO()
    manager = PDFResourceManager()
    converter = TextConverter(manager, output, laparams=LAParams())
    interpreter = PDFPageInterpreter(manager, converter)

    pagenums = set()
    for page in PDFPage.get_pages(infile, pagenums):
        interpreter.process_page(page)
    infile.close()
    converter.close()
    text = output.getvalue()
    output.close()

    result = []

    for line in text.split('\n'):
        line2 = line.strip()
        if line2 != '':
            result.append(line2)
    return (result)


def open_docx_file(file):
    temp = docx2txt.process(file)
    text = [line.replace('\t', ' ') for line in temp.split('\n') if line]
    text = [t for t in text if len(t) > 1]
    return (text)


def remove_punctuations(line):
    return re.sub(r'(\.|\,)', '', line)


def preprocess_document(document):
    for index, line in enumerate(document):
        line = line.lower()
        line = remove_punctuations(line)

        line = line.split(' ')
        while '' in line:
            line.remove('')

        while ' ' in line:
            line.remove(' ')

        document[index] = ' '.join(line)
    return (document)


def get_email(document):
    # Further optimization to be done.
    emails = []
    pattern = re.compile(r'\w+@[a-zA-Z_]+?\.[a-zA-Z]{2,3}')
    for line in document:
        matches = pattern.findall(line)
        for mat in matches:
            if len(mat) > 0:
                emails.append(mat)
    # print (emails)
    return (emails)


def get_phone_no(document):
    # This function has to be further modified better and accurate results.
    # Possible phone number formats - Including +91 or just with the numbers.

    mob_num_regex = r'''(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)
                        [-\.\s]*\d{3}[-\.\s]??\d{4}|\d{5}[-\.\s]??\d{4})'''
    pattern = re.compile(mob_num_regex)
    matches = []
    for line in document:
        match = pattern.findall(line)
        for mat in match:
            if len(mat) > 9:
                matches.append(mat)

    return (matches)


def get_education(document):
    education_terms = []
    with open('education.txt', 'r') as file:
        education_terms = file.readlines()

    education_terms = [term.strip('\n') for term in education_terms]
    education = []
    for line in document:
        for word in line.split(' '):
            if len(word) > 2 and word in education_terms:
                if line not in education:
                    education.append(line)
    # print (education)
    return (education)


def get_skills(document):
    skill_terms = []
    with open('valid_skills.txt', 'r') as file:
        skill_terms = file.readlines()

    skill_terms = [term.strip('\n') for term in skill_terms]
    skills = []

    for line in document:
        words = line.split(' ')

        for word in words:
            if word in skill_terms:
                if word not in skills:
                    skills.append(word)

        word_pairs = []
        for i in zip(words[:-1], words[1:]):
            word_pairs.append(i[0] + ' ' + i[
                1])  # This is to find skills like 'data science' i.e skills containint two words.    return (skills)

        for pair in word_pairs:
            if pair in skill_terms:
                if pair not in skills:
                    skills.append(pair)

    return (skills)


def get_experience(document):
    pattern1 = re.compile(
        r'(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?)(\s|\S)(\d{2,4}).*(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?)(\s|\S)(\d{2,4})')
    pattern2 = re.compile(r'(\d{2}(.|..)\d{4}).{1,4}(\d{2}(.|..)\d{4})')
    pattern3 = re.compile(r'(\d{2}(.|..)\d{4}).{1,4}(present)')
    pattern4 = re.compile(
        r'(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?)(\s|\S)(\d{2,4}).*(present)')
    patterns = [pattern1, pattern2, pattern3, pattern4]
    experience = []
    for index, line in enumerate(document):
        for pattern in patterns:
            exp = pattern.findall(line)
            if len(exp) > 0:
                experience.append(document[index:index + 4])

    return (experience)


def getParsedData(file):
    email_ids = []
    phone_nos = []
    education_1 = []
    education_2 = []
    skills_1 = []
    skills_2 = []
    experience_1 = []
    experience_2 = []
    file_name = file.filename
    if file_name.endswith('.pdf'):
        document = open_pdf_file(file)
    elif file_name.endswith('.docx'):
        document = open_docx_file(file)

    email = get_email(document)
    phone_no = get_phone_no(document)
    document = preprocess_document(document)
    # print ('\n\n')
    # print (file_name)
    # print ('Email is {} phone number is {}'.format(email, phone_no))
    if len(email_ids) > 0:
        email_ids.append(email[0])
    else:
        email_ids.append('')

    if len(phone_no) > 0:
        phone_nos.append(phone_no[0])
    else:
        phone_nos.append('')

    education = get_education(document)
    # print ('Education ', get_education(document))
    if len(education) > 1:
        education_1.append(education[0])
        education_2.append(education[1])
    elif len(education) == 1:
        education_1.append(education[0])
        education_2.append('')
    elif len(education) == 0:
        education_1.append('')
        education_2.append('')

    skills = get_skills(document)
    # print ('Skills ', skills)

    if len(skills) > 1:
        skills_1.append(skills[0])
        skills_2.append(skills[1])
    elif len(skills) == 1:
        skills_1.append(skills[0])
        skills_2.append('')
    elif len(skills) == 0:
        skills_1.append('')
        skills_2.append('')

    experience = get_experience(document)
    # print ('Experience ', get_experience(document))
    if len(experience) > 1:
        experience_1.append(experience[0])
        experience_2.append(experience[1])
    elif len(experience) == 1:
        experience_1.append(experience[0])
        experience_2.append('')
    elif len(experience) == 0:
        experience_1.append('')
        experience_2.append('')

    return {'email id':email_ids, 'phone nos':phone_nos, 'education 1':education_1, 'education 2':education_2, 'skills 1':skills_1, 'skills 2':skills_2, 'experience 1':experience_1, 'experiece 2':experience_2}


@app.route('/cv-parser', methods=['POST'])
def upload_file():
    # check if the post request has the file part
    if 'file' not in request.files:
        resp = jsonify({'message': 'No file part in the request'})
        resp.status_code = 400
        return resp
    file = request.files['file']
    if file.filename == '':
        resp = jsonify({'message': 'No file selected for uploading'})
        resp.status_code = 400
        return resp
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        data = getParsedData(file)
        resp = jsonify({
            'message': 'File parsed successfully',
            'payload': data
        })
        resp.status_code = 201
        return resp
    else:
        resp = jsonify({'message': 'Allowed file types are txt, pdf, png, jpg, jpeg, gif'})
        resp.status_code = 400
        return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
