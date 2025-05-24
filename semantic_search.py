from sentence_transformers import SentenceTransformer
import numpy as np

class SemanticSearchEngine:
    def __init__(self):
        # Load the all-MiniLM-L6-v2 model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def create_email_vector(self, email):
        # Create a text representation of the email
        # You can customize this to include more fields if needed
        if not isinstance(email, dict):
            raise ValueError("Email must be a dictionary with 'sender', 'subject', and 'body' keys.")
        
        # Ensure all required fields are present
        for field in ['sender', 'subject', 'body']:
            if field not in email:
                raise ValueError(f"Email is missing required field: {field}")
        text = (
            f"From: {email.get('sender', '')}\n"
            f"Subject: {email.get('subject', '')}\n"
            f"Body: {email.get('body', '')}"
        )
        return self.model.encode(text)

    def compute_and_save_embeddings(self, emails):
        # Only embed emails that don't have an embedding yet
        for email in emails:
            if 'embedding' not in email:
                email['embedding'] = self.create_email_vector(email).tolist()
        return emails

    def search(self, query, emails, top_k=10, min_score=0.5):
        # Compute query embedding
        query_vec = self.model.encode(query)
        # Prepare email embeddings
        email_embeddings = np.array([np.array(email['embedding']) for email in emails if 'embedding' in email])
        if len(email_embeddings) == 0:
            return []
        # Compute cosine similarities
        scores = np.dot(email_embeddings, query_vec) / (
            np.linalg.norm(email_embeddings, axis=1) * np.linalg.norm(query_vec) + 1e-10
        )
        # Get indices of emails above the threshold
        valid_indices = np.where(scores >= min_score)[0]
        if len(valid_indices) == 0:
            return []
        # Sort valid indices by score
        sorted_indices = valid_indices[np.argsort(scores[valid_indices])[::-1]]
        emails_with_embeddings = [email for email in emails if 'embedding' in email]
        # Return top_k emails above threshold
        return [emails_with_embeddings[i] for i in sorted_indices[:top_k]]

    def smart_search(self, query, emails, top_k=10, min_score=0.5):
        """
        Perform a smart search that first filters emails by sender/domain
        and then applies semantic search on the filtered set.
        """
        query_lower = query.lower()
        sender_keywords = []

        # Detect sender/domain search
        if "from " in query_lower:
            parts = query_lower.split("from ")
            if len(parts) > 1:
                sender_keywords.append(parts[1].strip())
        if "@" in query_lower:
            sender_keywords.append(query_lower.split("@")[-1].split()[0])

        filtered_emails = emails
        if sender_keywords:
            filtered_emails = [
                email for email in emails
                if any(kw in email.get('sender', '').lower() for kw in sender_keywords)
            ]
            # If user asks for "last" or "latest", sort by date and return the latest
            if "last" in query_lower or "latest" in query_lower:
                filtered_emails.sort(key=lambda e: e.get('date', ''), reverse=True)
                filtered_emails = filtered_emails[:1]

        if not filtered_emails:
            return []

        # If sender filter applied, optionally apply semantic search to filtered set
        # Or just return filtered_emails if "last"/"latest" was in query
        if sender_keywords and ("last" in query_lower or "latest" in query_lower):
            return filtered_emails

        # Otherwise, use semantic search
        return self.search(query, filtered_emails, top_k=top_k, min_score=min_score)

