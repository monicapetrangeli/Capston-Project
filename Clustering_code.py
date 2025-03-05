##PDF EMBEDDING
import os
import glob
import numpy as np
import pandas as pd
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

#Loading the embedding model that will be downloaded and stored locally
model=SentenceTransformer('all-MiniLM-L6-v2')

pdf_folder='path to pdfs'

#Opening each pdf file
def extract_text_from_pdf(pdf_path):
    text=''
    with open(pdf_path,'rb') as f:          #'rb' is a mode in python to open complex files like pdfs. 'r' is for simple text files
        reader=PdfReader(f)                 #with allows us to avoid having to call f.close() as it automatically stops once the file has been read
        for page in reader.pages:
            text+= page.extract_text() or ''
    return text

#Finding all pdf files within the pdf_folder such that we can iterate through them
pdf_paths=glob.glob(os.path.join(pdf_folder, '*.pdf'))
pdf_data=[]

#Iterating through all pdfs and saving their embedding into a list to then convert into a data frame
for pdf_path in pdf_paths:
    text=extract_text_from_pdf(pdf_path)
    embedding=model.encode(text,convert_to_numpy=True)
    pdf_data.append({
        'path': pdf_path,
        'embedding':embedding,
        'text':text
    })
embedded_pdfs=pd.DataFrame(pdf_data)

##CLUSTERING PDFS FOR MAIN LABELS
#Transforming embeddings data frame into a matrix
X=np.vstack(embedded_pdfs['embedding'].values)

#Setting up KMeans clustering model
n_clusters='number of main labels'
kmeans=KMeans(n_clusters,random_state=42)
#Predicting main label based on the cluster and storing the prediction in the data frame
embedded_pdfs['main_cluster']=kmeans.fit_predict(X)
labels=kmeans.fit_predict(X)

#Checking the model performance
print(kmeans.inertia_)          #A lower inertia is prefered, demonstyrating how well pdfs fit into their respective clusters
print(silhouette_score(X,labels))       #A score closer to 1 is preferd to show well-separated clusters, if a score of around 0 is found there is an overlapping of clusters. We don't want a negative score

#MAPPING CLUSTERS TO MAIN LABELS
#Saving the centroid of each cluster
centroids=kmeans.cluster_centers_

#Computing  the similarity between centroid and each pdf within the cluster to find  the best representative pdf of the cluster
similarities = cosine_similarity(centroids, X)
most_representative_indices = similarities.argmax(axis=1)
most_representative_documents = [embedded_pdfs.iloc[i] for i in most_representative_indices]

#Extracting the main labels
labels_data=pd.read_csv('path to labels csv')
main_labels=labels_data['column of main labels'].unique()

def assign_label_to_cluster(cluster_index,document,main_labels):
    #we can key_work match, use NLP techniques (recommended) or title/content of the document
    document_content=document['text']
    for label in main_labels:
        if label.lower() in document_content.lower():       #simply matching is the word of the label is found in the pdf, NEEDS TO BE CHANGED!
            return label
    return 'Unknown'        #if there is no match

cluster_to_label={}

for cluster_index, doc in enumerate(most_representative_documents):
    label=assign_label_to_cluster(cluster_index,doc,main_labels)
    cluster_to_label[cluster_index]=label

#Saving the main label in the data frame mapping based on main_cluster
embedded_pdfs['main_label']=embedded_pdfs['main_cluster'].map(cluster_to_label)

#CLUSTERING AGAIN FOR SUB LABELS
#Extracting all sub labels
sub_labels=labels_data['column sub label'].unique().tolist()

for label in main_labels:
    X=np.vstack(embedded_pdfs[embedded_pdfs['main_label']==label]['embedding'].values)
    
    #Setting up KMeans clustering model for sub_labels
    n_clusters='number of sub labels'
    kmeans=KMeans(n_clusters,random_state=42)
    embedded_pdfs.loc[embedded_pdfs['main_label']==label, 'sub_cluster'] = kmeans.fit_predict(X)
    labels=kmeans.fit_predict(X)

    #Checking the model performance for each sub cluster
    print(kmeans.inertia_)          #A lower inertia is prefered, demonstyrating how well pdfs fit into their respective clusters
    print(silhouette_score(X,labels))       #A score closer to 1 is preferd to show well-separated clusters, if a score of around 0 is found there is an overlapping of clusters. We don't want a negative score

    #MAPPING SUB CLUSTERS TO SUB LABELS
    #Saving the centroid of each cluster
    centroids=kmeans.cluster_centers_

    #Computing  the similarity between centroid and each pdf within the cluster to find  the best representative pdf of the cluster
    similarities = cosine_similarity(centroids, X)
    most_representative_indices = similarities.argmax(axis=1)
    most_representative_documents = [embedded_pdfs.iloc[i] for i in most_representative_indices]

    sub_cluster_to_label={}

    for cluster_index, doc in enumerate(most_representative_documents):
        label=assign_label_to_cluster(cluster_index,doc,sub_labels)
        sub_cluster_to_label[cluster_index]=label

    #Saving the sub label in the data frame mapping based on sub_cluster
    embedded_pdfs[embedded_pdfs['main_label']==label]['sub_label']=embedded_pdfs[embedded_pdfs['main_label']==label]['sub_cluster'].map(sub_cluster_to_label)