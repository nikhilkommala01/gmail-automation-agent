import os
import openai


class OpenAIClient:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise EnvironmentError('OPENAI_API_KEY is not set')
        openai.api_key = self.api_key
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    def summarize_emails(self, emails):
        # emails: list of dicts with keys 'subject', 'from', 'snippet'
        combined = ''
        for i, e in enumerate(emails, start=1):
            combined += f"Email {i}: From: {e.get('from')} | Subject: {e.get('subject')}\nSnippet: {e.get('snippet')}\n\n"

        prompt = (
            "You are an assistant that summarizes the following unread emails. "
            "Produce a concise bulleted summary and list suggested quick actions (reply, archive, mark as important).\n\n"
            "Here are the emails:\n\n" + combined
        )

        resp = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You summarize emails concisely."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.2,
        )
        text = resp['choices'][0]['message']['content'].strip()
        return text
