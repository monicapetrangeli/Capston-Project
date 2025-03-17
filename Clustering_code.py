##PDF EMBEDDING
import os
import glob
import numpy as np
import pandas as pd
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, adjusted_rand_score, v_measure_score, davies_bouldin_score, calinski_harabasz_score, classification_report
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression


#Loading the embedding model that will be downloaded and stored locally
model=SentenceTransformer('all-MiniLM-L6-v2')

pdf_folder='.\Capstone_CM\Documents Database'

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
n_clusters=3          #does this mean that all labels should be present for the clustering to work well? What if I can save the given clusters and then simply check for each new pdf in what of the original clusters he would be part of.
kmeans=KMeans(n_clusters,random_state=42)
#Predicting main label based on the cluster and storing the prediction in the data frame
embedded_pdfs['main_cluster']=kmeans.fit_predict(X)
labels=kmeans.fit_predict(X)

#Checking the model performance
print(kmeans.inertia_)          #A lower inertia is prefered, demonstyrating how well pdfs fit into their respective clusters
print(silhouette_score(X,labels))       #A score closer to 1 is preferd to show well-separated clusters, if a score of around 0 is found there is an overlapping of clusters. We don't want a negative score
print(f"Adjusted Rand Index (ARI): {adjusted_rand_score(labels, embedded_pdfs['main_cluster'])}")       # Closer to 0 = random clustering
print(f"V-Measure: {v_measure_score(labels, embedded_pdfs['main_cluster'])}")       #High better
print(f"Davies-Bouldin Index (DBI): {davies_bouldin_score(X, labels)}")             #Lower = better separated
print(f"Calinski-Harabasz Index (CH): {calinski_harabasz_score(X, labels)}")        #Higher=better separated

#MAPPING CLUSTERS TO MAIN LABELS
#Saving the centroid of each cluster
centroids=kmeans.cluster_centers_

#Computing  the similarity between centroid and each pdf within the cluster to find  the best representative pdf of the cluster
similarities = cosine_similarity(centroids, X)
most_representative_indices = similarities.argmax(axis=1)
most_representative_documents = [embedded_pdfs.iloc[i] for i in most_representative_indices]

#Defining main labels
cluster_to_label = {
    0: 'Admin',
    1: 'Other',
    2: 'Email'
}

# Map the cluster number to the label
embedded_pdfs['main_label'] = embedded_pdfs['main_cluster'].map(cluster_to_label)


#CLUSTERING AGAIN FOR MEDICAL AND LEGAL IN THE OTHER MAIN LABEL
# Filter only the "Other" cluster
admin_docs = embedded_pdfs[embedded_pdfs['main_label'] == 'Other']

# Ensure there are enough samples for clustering
if len(admin_docs) >= 2:
    X = np.vstack(admin_docs['embedding'].values)
    
    # Setting up KMeans clustering model for sub-clusters
    n_clusters = 2
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    
    # Predict sub-clusters
    sub_labels = kmeans.fit_predict(X)
    embedded_pdfs.loc[embedded_pdfs['main_label'] == 'Other', 'sub_cluster'] = sub_labels
    
    # Checking the model performance
    print("Inertia:", kmeans.inertia_)  # Lower inertia is better
    print("Silhouette Score:", silhouette_score(X, sub_labels))  # Closer to 1 is better
    print(f"Adjusted Rand Index (ARI): {adjusted_rand_score(sub_labels, embedded_pdfs.loc[embedded_pdfs['main_label'] == 'Other', 'sub_cluster'])}")       # Closer to 0 = random clustering
    print(f"V-Measure: {v_measure_score(sub_labels, embedded_pdfs.loc[embedded_pdfs['main_label'] == 'Other', 'sub_cluster'])}")       #High better
    print(f"Davies-Bouldin Index (DBI): {davies_bouldin_score(X, sub_labels)}")             #Lower = better separated
    print(f"Calinski-Harabasz Index (CH): {calinski_harabasz_score(X, sub_labels)}")        #Higher=better separated

    # Saving the centroid of each cluster
    centroids = kmeans.cluster_centers_

    # Computing similarity between centroid and each document
    similarities = cosine_similarity(centroids, X)
    most_representative_indices = similarities.argmax(axis=1)
    
    # Find the most representative documents for each sub-cluster
    most_representative_documents = [admin_docs.iloc[i] for i in most_representative_indices]

    #Defining sub labels
    cluster_to_sub_label = {
        0: 'Medical',
        1: 'Legal'
    }
    # Map the sub cluster number to the label
    embedded_pdfs['sub_label'] = embedded_pdfs['sub_cluster'].map(cluster_to_sub_label)


#CLUSTERING SUB LABELS
for i in range(0,len(cluster_to_sub_label)):
    docs = embedded_pdfs[embedded_pdfs['sub_cluster'] == i]

    # Ensure there are enough samples for clustering
    if len(docs) >= 2:
        X = np.vstack(docs['embedding'].values)
        
        # Setting up KMeans clustering model for sub-clusters
        n_clusters = 'number of sub_sub_cluster'
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        
        # Predict sub-clusters
        sub_labels = kmeans.fit_predict(X)
        embedded_pdfs.loc[embedded_pdfs['sub_cluster'] == i, 'sub_cluster_2'] = sub_labels
        
        # Checking the model performance
        print("Inertia:", kmeans.inertia_)  # Lower inertia is better
        print("Silhouette Score:", silhouette_score(X, sub_labels))  # Closer to 1 is better
        
        # Saving the centroid of each cluster
        centroids = kmeans.cluster_centers_

        # Computing similarity between centroid and each document
        similarities = cosine_similarity(centroids, X)
        most_representative_indices = similarities.argmax(axis=1)
        
        # Find the most representative documents for each sub-cluster
        most_representative_documents = [admin_docs.iloc[i] for i in most_representative_indices]

        print(embedded_pdfs[embedded_pdfs['sub_cluster'] == i])

        #Defining sub sub labels
        cluster_to_sub_label = {
            0: '...',
            1: '...'
        }
        # Map the sub sub cluster number to the label
        embedded_pdfs['sub_label_2'] = embedded_pdfs['sub_cluster2'].map(cluster_to_sub_label)
