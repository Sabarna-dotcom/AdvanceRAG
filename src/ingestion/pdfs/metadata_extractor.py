class MetadataExtractor:

    SUBJECT_KEYWORDS = {
        "machine learning": "AI",
        "neural network": "Deep Learning",
        "database": "DBMS",
        "cloud": "Cloud Computing",
        "security": "Cybersecurity",
    }

    def extract_topics(self, text: str):

        text_lower = text.lower()

        topics = []

        for keyword, topic in self.SUBJECT_KEYWORDS.items():
            if keyword in text_lower:
                topics.append(topic)

        return list(set(topics))

    def detect_difficulty(self, text: str):

        word_count = len(text.split())

        if word_count < 80:
            return "beginner"

        elif word_count < 200:
            return "intermediate"

        return "advanced"
