##PDF EMBEDDING
import os
import glob
import numpy as np
import pandas as pd
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score, v_measure_score, davies_bouldin_score, calinski_harabasz_score, classification_report
from sklearn.metrics.pairwise import cosine_similarity
import re

#Loading the embedding model that will be downloaded and stored locally
model=SentenceTransformer('all-MiniLM-L6-v2')

pdf_folder=r'.\Capstone_CM\Documents Database'

#Opening each pdf file
def extract_text_from_pdf(pdf_path):
    text=''
    with open(pdf_path,'rb') as f:          #'rb' is a mode in python to open complex files like pdfs. 'r' is for simple text files
        reader=PdfReader(f)                 #with allows us to avoid having to call f.close() as it automatically stops once the file has been read
        for page in reader.pages:
            text+= page.extract_text() or ''
    return text.lower()

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
print("Main Clustering Performance")
print("Inertia:", kmeans.inertia_)          #A lower inertia is prefered, demonstyrating how well pdfs fit into their respective clusters
print("Silhouette Score:", silhouette_score(X,labels))       #A score closer to 1 is preferd to show well-separated clusters, if a score of around 0 is found there is an overlapping of clusters. We don't want a negative score
print(f"Adjusted Rand Index (ARI): {adjusted_rand_score(labels, embedded_pdfs['main_cluster'])}")       # Closer to 0 = random clustering
print(f"V-Measure: {v_measure_score(labels, embedded_pdfs['main_cluster'])}")       #High better
print(f"Davies-Bouldin Index (DBI): {davies_bouldin_score(X, labels)}")             #Lower = better separated
print(f"Calinski-Harabasz Index (CH): {calinski_harabasz_score(X, labels)}")        #Higher = better separated

print(embedded_pdfs)
#MAPPING CLUSTERS TO MAIN LABELS
#Saving the centroid of each cluster
centroids_main=kmeans.cluster_centers_

#Computing  the similarity between centroid and each pdf within the cluster to find  the best representative pdf of the cluster
similarities = cosine_similarity(centroids_main, X)
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


#CLUSTERING AGAIN FOR MEDICAL AND LEGAL
# Filter only the "Other" cluster
admin_docs = embedded_pdfs[embedded_pdfs['main_label'] == 'Other']

# Ensure there are enough samples for clustering
if len(admin_docs) >= 2:
    X = np.vstack(admin_docs['embedding'].values)
    
    # Setting up KMeans clustering model for sub-clusters
    n_clusters = 2
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)

    centroids_other=kmeans.cluster_centers_

    # Predict sub-clusters
    sub_labels = kmeans.fit_predict(X)
    admin_docs = admin_docs.copy()  # Avoid SettingWithCopyWarning
    admin_docs['sub_cluster'] = sub_labels
    
    # Checking the model performance
    print("Inertia:", kmeans.inertia_)  # Lower inertia is better
    print("Silhouette Score:", silhouette_score(X, sub_labels))  # Closer to 1 is better
    print(f"Adjusted Rand Index (ARI): {adjusted_rand_score(sub_labels, admin_docs['sub_cluster'])}")  # Closer to 0 = random clustering
    print(f"V-Measure: {v_measure_score(sub_labels, admin_docs['sub_cluster'])}")  # High better
    print(f"Davies-Bouldin Index (DBI): {davies_bouldin_score(X, sub_labels)}")  # Lower = better separated
    print(f"Calinski-Harabasz Index (CH): {calinski_harabasz_score(X, sub_labels)}")  # Higher = better separated

    # Update the main_label based on the sub-cluster
    admin_docs.loc[admin_docs['sub_cluster'] == 0, 'main_label'] = 'Medical'
    admin_docs.loc[admin_docs['sub_cluster'] == 1, 'main_label'] = 'Legal'

    # Reflect the changes in the main DataFrame
    embedded_pdfs.update(admin_docs)
    
#SUB-LABELS 
#Defining the list of features each sub lable must have
document_features = {
    "ACKNOWLEDGMENT OF RECEIPT": {
        "keywords": ["acknowledge receipt", "received by", "confirmation of receipt", "this is to confirm"],
        "entities": ["person", "date"]
    },
    "ACTS": {
        "keywords": ["act", "article", "section", "in accordance with", "decree"],
        "entities": ["law reference", "date"]
    },
    "RESOLUTIONS OR CLOSURE": {
        "keywords": ["resolved", "resolution", "closure", "final decision", "case closed"],
        "entities": ["case number", "date"]
    },
    "NOTICES": {
        "keywords": ["notice is hereby", "public notice", "this is to inform", "announcement"],
        "entities": ["date", "location"]
    },
    "REPORTS": {
        "keywords": ["findings", "summary", "report", "results", "conclusions"],
        "entities": ["date", "person"]
    },
    "GUARANTEES OR DEPOSITS": {
        "keywords": ["deposit", "guarantee", "secured by", "financial assurance"],
        "entities": ["amount", "date", "bank"]
    },
    "ADMINISTRATIVE": {
        "keywords": ["administrative", "memo", "department", "request", "internal"],
        "entities": ["department", "official"]
    },
    "PRELIMINARY PROCEEDINGS": {
        "keywords": ["preliminary", "initial hearing", "case opening", "early stage"],
        "entities": ["case number", "court"]
    },
    "PAYMENTS OR COMPENSATIONS": {
        "keywords": ["payment", "compensation", "reimbursement", "amount due", "paid on"],
        "entities": ["amount", "date", "recipient"]
    },
    "APPEAL": {
        "keywords": ["appeal", "appeal submitted", "grounds for appeal", "appellant"],
        "entities": ["court", "case number"]
    },
    "POWER OF ATTORNEY": {
        "keywords": ["power of attorney", "appoint", "authorize", "behalf"],
        "entities": ["person", "authority", "date"]
    },
    "SENTENCE": {
        "keywords": ["sentenced to", "court finds", "verdict", "judgment"],
        "entities": ["date", "judge", "sentence length"]
    },
    "MEDICAL HISTORY": {
        "keywords": ["history of", "past conditions", "medical history"],
        "entities": ["date", "medical condition"]
    },
    "MEDICAL CERTIFICATE": {
        "keywords": ["medical certificate", "certify that", "unfit for work"],
        "entities": ["doctor", "patient", "date"]
    },
    "INITIAL CLINICAL DIAGNOSIS": {
        "keywords": ["initial diagnosis", "preliminary finding", "clinical assessment"],
        "entities": ["medical condition", "doctor", "date"]
    },
    "SEQUELAE STABILIZATION": {
        "keywords": ["sequelae", "stabilized", "residual condition", "follow-up"],
        "entities": ["medical condition", "date", "doctor"]
    }
}

#Creating a function to classify each document based on keywords
def match_keywords(text, keywords):
    return [kw for kw in keywords if kw.lower() in text]

#Creating a fucnstion to extract the entities
def extract_entity(text):
    entities = {}
    entities["person"] = re.findall(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", text)  # Matches names like "John Doe"
    entities["date"] = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)  # Matches dates like "2025-04-21"
    entities["law reference"] = re.findall(r"\bArticle\s\d+\b", text)  # Matches references like "Article 12"
    entities["case number"] = re.findall(r"\bCase\sNo\.\s\d+\b", text)  # Matches case numbers like "Case No. 12345"
    entities["location"] = re.findall(r"\b(?:City|Town|Village|District|Region):\s[A-Z][a-z]+\b", text)  # Matches locations
    entities["amount"] = re.findall(r"\$\d+(,\d{3})*(\.\d{2})?", text)  # Matches amounts like "$1,000.00"
    entities["bank"] = re.findall(r"\b[A-Z][a-z]+\s(Bank|Finance|Institution)\b", text)  # Matches bank names like "ABC Bank"
    entities["department"] = re.findall(r"\bDepartment:\s[A-Z][a-z]+\b", text)  # Matches department names
    entities["official"] = re.findall(r"\bOfficial:\s[A-Z][a-z]+\s[A-Z][a-z]+\b", text)  # Matches official names
    entities["court"] = re.findall(r"\bCourt\s[A-Z][a-z]+\b", text)  # Matches court names like "Court of Appeals"
    entities["recipient"] = re.findall(r"\bRecipient:\s[A-Z][a-z]+\s[A-Z][a-z]+\b", text)  # Matches recipient names
    entities["authority"] = re.findall(r"\bAuthority:\s[A-Z][a-z]+\b", text)  # Matches authority names
    entities["judge"] = re.findall(r"\bJudge\s[A-Z][a-z]+\b", text)  # Matches judge names like "Judge Smith"
    entities["sentence length"] = re.findall(r"\b\d+\s(?:years?|months?|days?)\b", text)  # Matches sentence lengths like "5 years"
    entities["medical condition"] = re.findall(r"\b(?:condition|diagnosis|disease|injury)\b", text, re.IGNORECASE)  # Matches medical conditions
    entities["patient"] = re.findall(r"\bPatient:\s[A-Z][a-z]+\s[A-Z][a-z]+\b", text)  # Matches patient names
    entities["doctor"] = re.findall(r"\bDoctor:\s[A-Z][a-z]+\s[A-Z][a-z]+\b", text)  # Matches doctor names
    return entities

def classify_document(text, document_features):
    matched = {}
    ents = extract_entity(text)

    for label, features in document_features.items():
        score = 0
        matched_keywords = match_keywords(text, features.get("keywords", []))
        score += len(matched_keywords)
        
        for ent_type in features.get("entities", []):
            if ents.get(ent_type):
                score += 1
        
        matched[label] = score
    
    top_labels = sorted(matched.items(), key=lambda x: x[1], reverse=True)
    #Returning OTHER whenever a best match is not found
    if not top_labels or top_labels[0][1] == 0:
        return ["OTHER", None, None]
    
    top_labels = [label for label, score in top_labels[:3]]
    while len(top_labels) < 3:
        top_labels.append("OTHER")

    return top_labels

embedded_pdfs[['sub_label_1', 'sub_label_2', 'sub_label_3']] = embedded_pdfs['text'].apply(
    lambda text: pd.Series(classify_document(text, document_features))
)

print(embedded_pdfs[['main_label', 'sub_label_1', 'sub_label_2', 'sub_label_3']])

def process_new_pdf(pdf_path, embedded_pdfs):
    text = extract_text_from_pdf(pdf_path)
    embedding = model.encode(text, convert_to_numpy=True)

    # Step 2: Assign the main label based on the closest centroid
    main_cluster_index = np.argmax(cosine_similarity([embedding], centroids_main))
    main_label = list(cluster_to_label.values())[main_cluster_index]

    # Step 3: If the main label is "Other," assign medical/legal label
    if main_label == "Other":
        sub_cluster_index = np.argmax(cosine_similarity([embedding], centroids_other))
        main_label = "Medical" if sub_cluster_index == 0 else "Legal"

    # Step 4: Assign sub-labels using the classify_document function
    sub_labels = classify_document(text, document_features)

    # Step 5: Add the new PDF to the DataFrame
    new_pdf_data = {
        'path': pdf_path,
        'embedding': embedding,
        'text': text,
        'main_label': main_label,
        'sub_label_1': sub_labels[0],
        'sub_label_2': sub_labels[1],
        'sub_label_3': sub_labels[2]
    }
    embedded_pdfs = embedded_pdfs.append(new_pdf_data, ignore_index=True)

    return embedded_pdfs
