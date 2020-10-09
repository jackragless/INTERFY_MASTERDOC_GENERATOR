#PURPOSE: scrapes all data from IT company help guides site and creates master guide PDF document. Stored in Google Drive and uodated hourly using API.

#gdrive api libs
from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient.http import MediaFileUpload

#other libs
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import pdfkit 
import re
from pdfrw import PdfReader, PdfWriter
import os
import datetime
import time 
requests.packages.urllib3.disable_warnings()


#prevents warnings when scraping without headers
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
except AttributeError:
    pass




#scrapes html from given link and converts to bs4 object
def extract_html(link):
    try:
        resp = requests.get(link, verify=False)
        soup2 = BeautifulSoup(resp.content,"html.parser")
        return soup2
    except:
        return "!@#$CONNECTION_FAILURE"




#Links to current help article categories; update if website structure updated
xero_cat_link = ['https://help.interfy.com.au/index.php/article-categories/onboarding-xero/', 'https://help.interfy.com.au/index.php/article-categories/mapping-in-onecore-xero/','https://help.interfy.com.au/index.php/article-categories/transactions-xero/','https://help.interfy.com.au/index.php/article-categories/faq-xero/']
myob_cat_link = ['https://help.interfy.com.au/index.php/article-categories/onboarding-myob/','https://help.interfy.com.au/index.php/article-categories/mapping-in-onecore-myob/','https://help.interfy.com.au/index.php/article-categories/transactions-myob/','https://help.interfy.com.au/index.php/article-categories/faq-myob/']




#fetches URLs contained within above pages
def extract_links(array):
    final = []
    for link in array:
        soup = extract_html(link)
        temp = []
        
        for a in soup.find_all('a', {"class": "hkb-article__link"}, href = True):
            temp.append(a["href"]);
        
        if soup.find('a', {"class": "hkb-category__link"}):
            for sl in soup.find_all('a', {"class": "hkb-category__link"}, href = True):
                sublink = extract_html(sl['href'])
                for sl_2 in sublink.find_all('a', {"class": "hkb-article__link"}, href = True):
                    temp.append(sl_2["href"])
          
        final.append(temp)
        
    return final
                




#fetches body of html content from wordpress site and adds to site object list
def fetch_article_content(array):
    final = []
    for i in range(len(array)):
        temp = []
        for j in range(len(array[i])):
            soup = extract_html(array[i][j])

            if soup and isinstance(soup,str)==False:
                if soup.find('figure'):

                    soup.figure.decompose()

                title = soup.find("h1", {"class": "hkb-article__title"})

                extract = (str(soup.find("h1", {"class": "hkb-article__title"})) + str(soup.find("div", {"class": "pf-content"}))).replace('<div class="pf-content">','').replace('</div>','')

                item = {
                    "link":array[i][j],
                    "title":title.text,
                    "html": extract
                }
                
                temp.append(item)
            
        final.append(temp)
        
    return final




#appends all html from fetch_article_content() array into one strings
def combine_all_html(master):

	#adds CSS to improve later PDF conversion
    
    style = """
    <meta charset="UTF-8" />
    <style> 
    h1,h5,div{page-break-before: always;} 
    h3,h2{padding-top: 35px;}
    div{page-break-inside: avoid;}
    body{font-size:24pt}
    li{margin-top: 60px}
    </style>
    """
    
    final = []

    for i in range(len(master)):

    	#This autogenerates a contents page for the document
        
        directory = '<div> <h1>Contents</h1> <ol style = "list-style-type: decimal-leading-zero;">'

        temp = ''

        for j in range(len(master[i])):
            
            directory = directory + ' <li> ' + master[i][j]['title'] + ' </li> '
            temp += master[i][j]['html']
         
        directory += ' </ol> </div>'
        temp = style + directory + temp
        final.append(temp)
    
    return final




#Adds numbers to each article which can later 
def add_heading_numbers(obj):
    for i in range(len(obj)):

        k = 0

        for j in range(len(obj[i])):

            k += 1
            obj[i][j]['html'] = obj[i][j]['html'].replace('itemprop="headline">', 'itemprop="headline">{}) '.format(k))
    return




#finally converts html into PDF using pdfkit library. Existing titlepages are added sequentially.
def generate_pdf(combined_arr, platform):
    
    cp = PdfReader('cover_page.pdf')
    doc_name = ['onboarding.pdf', 'mapping.pdf', 'transactions.pdf', 'faq.pdf']

    options = {      
        'margin-left': '10mm',
        'margin-right': '10mm',
        'margin-bottom': '15mm',
        'margin-top': '15mm'
        }
    
    superdoc = PdfWriter()
    
    if platform == 'xero':
        superdoc.addpage(cp.pages[0])
        superdoc_name = 'xero_master.pdf'
    elif platform == 'myob':
        superdoc.addpage(cp.pages[1])
        superdoc_name = 'myob_master.pdf'
    
    
    for i in range(len(combined_arr)):
        pdfkit.from_string(combined_arr[i], '{}'.format(doc_name[i]), options=options)
        temp_pdf = PdfReader('{}'.format(doc_name[i]))
        superdoc.addpage(cp.pages[2+i])
        for j in temp_pdf.pages[1:]:
            superdoc.addpage(j)
            
        os.remove('{}'.format(doc_name[i]))
        
    superdoc.write(superdoc_name)
    return





#Google drive API used to store constantly updated document. Hence, avoided paying for AWS S3 storage plus google links are easier to provide.

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
            
    file = service.files().get(fileId='1WbEzL0W7x8DKzTZypYxGyaK1sRWhOqdJ').execute()
    media = MediaFileUpload('xero_master.pdf', mimetype='application/pdf')
    updated_file = service.files().update(fileId='1WbEzL0W7x8DKzTZypYxGyaK1sRWhOqdJ', media_body=media).execute()
    
    file = service.files().get(fileId='1seUKNPE9FFtr2PXBD7QLBBKODhSB7l1v').execute()
    media = MediaFileUpload('myob_master.pdf', mimetype='application/pdf')
    updated_file = service.files().update(fileId='1seUKNPE9FFtr2PXBD7QLBBKODhSB7l1v', media_body=media).execute()






#driver function

def execute():
    xero_art_link = extract_links(xero_cat_link)
    myob_art_link = extract_links(myob_cat_link)
    
    xero_master = fetch_article_content(xero_art_link)
    myob_master = fetch_article_content(myob_art_link)
    
    add_heading_numbers(xero_master)
    add_heading_numbers(myob_master)
    
    xero_combined = combine_all_html(xero_master)
    myob_combined = combine_all_html(myob_master)

    #adding time generated to document
    
    xero_combined[3] += '<h5>Time Generated: {}</h5>'.format(str(datetime.datetime.now()))
    myob_combined[3] += '<h5>Time Generated: {}</h5>'.format(str(datetime.datetime.now()))
    
    generate_pdf(xero_combined,'xero')
    generate_pdf(myob_combined,'myob')
    
    main()
    
    return
    


#update every 60mins on AWS server; easier than implementing Lambda.
condition = True
while(condition==True):
    execute()
    time.sleep(3600)



