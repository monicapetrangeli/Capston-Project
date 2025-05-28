## CLUSTERING APPROACH TO FIND SIMILAR CASES
import os
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

#Loading the embedding model as in the clustering file
model = SentenceTransformer('all-MiniLM-L6-v2')

#Define the folder containing all case folders
case_folder = r'.\Capstone_CM\Documents Database'

#Function to extract text and embeddings for all documents in a case folder
def process_case_folder(folder_path):
    case_data = {}
    for subfolder_name in os.listdir(folder_path):
        subfolder_path = os.path.join(folder_path, subfolder_name)
        if os.path.isdir(subfolder_path): 
            case_data[subfolder_name] = {}
            for file_name in os.listdir(subfolder_path):
                if file_name.endswith('.pdf'):
                    file_path = os.path.join(subfolder_path, file_name)
                    text = extract_text_from_pdf(file_path)
                    embedding = model.encode(text, convert_to_numpy=True)
                    case_data[subfolder_name][file_name] = embedding
    return case_data

#Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    from PyPDF2 import PdfReader
    text = ''
    with open(pdf_path, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ''
    return text.lower()

#Process all documents in each case folder
cases = {}
for case_name in os.listdir(case_folder):
    case_path = os.path.join(case_folder, case_name)
    if os.path.isdir(case_path):
        cases[case_name] = process_case_folder(case_path)

#Function to compute similarity between two cases
def compute_case_similarity(case1, case2):
    similarity_scores = []
    for doc1_name, doc1_embedding in case1.items():
        for doc2_name, doc2_embedding in case2.items():
            sim = cosine_similarity([doc1_embedding], [doc2_embedding])[0][0]
            similarity_scores.append(sim)
    return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0

#Compare all pairs of cases and impute similarity function
case_similarities = {}
for case1_name in cases:
    for case2_name in cases:
        if case1_name != case2_name:
            similarity = compute_case_similarity(cases[case1_name], cases[case2_name])
            case_similarities[(case1_name, case2_name)] = similarity

#Find the three most similar cases for each case
top_similar_cases = {}
for case_name in cases:
    #Get all pairs where this case is involved and the other case is not itself
    similar_cases = []
    for (case1, case2), sim in case_similarities.items():
        if case1 == case_name and case2 != case_name:
            similar_cases.append((case2, sim))
        elif case2 == case_name and case1 != case_name:
            similar_cases.append((case1, sim))
    #Sort by similarity descending and take top 3
    top_three = sorted(similar_cases, key=lambda x: x[1], reverse=True)[:3]
    top_similar_cases[case_name] = top_three

#Print the three most similar cases and their similarity percentages
for case, similars in top_similar_cases.items():
    print(f"\nThe three most similar cases to {case} are:")
    for other_case, sim in similars:
        print(f"  {other_case}: {sim*100:.2f}% similarity")