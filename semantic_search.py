# from openai import OpenAI
# import numpy as np
# import os

# class SemanticSearchEngine:
#     def __init__(self):
#         # Initialize OpenAI client
#         self.client = OpenAI(
#             api_key=os.getenv('OPENAI_API_KEY')  # Make sure to set this environment variable
#         )
    
#     def create_email_vector(self, email):
#         # Combine all relevant fields for embedding
#         text = f"Subject: {email['subject']} \n" \
#                f"From: {email['sender']} \n" \
#                f"To: {email.get('to', '')} \n" \
#                f"Date: {email['date']} \n" \
#                f"Body: {email['body']}"
        
#         # Get embeddings from OpenAI
#         response = self.client.embeddings.create(
#             model="text-embedding-ada-002",
#             input=text
#         )
#         return response.data[0].embedding
    
#     def compute_and_save_embeddings(self, emails):
#         # Get all emails without embeddings
#         emails_without_embeddings = [email for email in emails if 'embedding' not in email]
        
#         for email in emails_without_embeddings:
#             text = f"Subject: {email['subject']} \n" \
#                    f"From: {email['sender']} \n" \
#                    f"To: {email.get('to', '')} \n" \
#                    f"Date: {email['date']} \n" \
#                    f"Body: {email['body']}"
            
#             # Get embeddings from OpenAI
#             response = self.client.embeddings.create(
#                 model="text-embedding-ada-002",
#                 input=text
#             )
#             email['embedding'] = response.data[0].embedding
        
#         return emails
    
#     def search(self, query, emails, top_k=10):
#         # Get query embedding
#         query_response = self.client.embeddings.create(
#             model="text-embedding-ada-002",
#             input=query
#         )
#         query_embedding = np.array(query_response.data[0].embedding)
        
#         # Prepare email embeddings matrix
#         email_embeddings = np.array([email.get('embedding', self.create_email_vector(email)) 
#                                     for email in emails])
        
#         # Compute all similarities at once
#         scores = np.dot(email_embeddings, query_embedding)
        
#         # Get top k indices
#         top_indices = np.argsort(scores)[-top_k:][::-1]
        
#         # Return only emails without scores
#         return [emails[i] for i in top_indices]