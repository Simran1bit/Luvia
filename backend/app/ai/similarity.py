from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim


# Load a pretrained model for comparing text meaning.
model = SentenceTransformer("all-MiniLM-L6-v2")


def compare_reports(report_a: str, report_b: str) -> float:
    """Return a cosine similarity score between two reports."""

    # Convert both reports into numerical embeddings.
    embeddings = model.encode([report_a, report_b])

    # Compare the vectors.
    score = cos_sim(embeddings[0], embeddings[1]).item()

    return round(float(score), 4)


if __name__ == "__main__":
    report_a = "Heavy rainfall was reported in Gurugram."
    report_b = "Gurugram experienced intense rain."

    report_c = "A heatwave is affecting Rajasthan."

    print("Similar reports:", compare_reports(report_a, report_b))
    print("Different reports:", compare_reports(report_a, report_c))
