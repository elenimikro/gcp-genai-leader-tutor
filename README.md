# GCP Generative AI Leader Tutor

[![Google Cloud Certification](https://img.shields.io/badge/Google%20Cloud-Generative%20AI%20Leader-4285F4?style=flat&logo=googlecloud&logoColor=white)](https://cloud.google.com/learn/certification/generative-ai-leader)

A local CLI study tool to help you prepare for the [Google Cloud Generative AI Leader certification](https://cloud.google.com/learn/certification/generative-ai-leader).

## Features

- **39-day structured study plan** covering all 4 exam domains and every subtopic
- **122 practice questions** with detailed explanations
- **78 flashcards** with SM-2 spaced repetition (cards resurface at optimal intervals)
- **Readiness dashboard** with weighted score (quiz 50%, flashcards 30%, completion 20%)
- **Weak area review** — automatically identifies and drills low-scoring topics
- 100% offline — all data stored locally in `~/.genai_tutor/tutor.db`

## Exam Domains

| # | Domain | Weight |
|---|--------|--------|
| 1 | Fundamentals of Generative AI | 30% |
| 2 | Google Cloud Gen AI Products & Strategy | 35% |
| 3 | Techniques to Improve Gen AI Model Output | 20% |
| 4 | Business Strategies for Successful AI Adoption | 15% |

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/elenimikro/gcp-genai-leader-tutor.git
cd gcp-genai-leader-tutor
```

Create and activate a virtual environment:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

Install the package:

```bash
pip install -e .
```

## Usage

### Interactive mode (recommended)
```bash
genai-tutor
```
Then type commands at the `>` prompt: `study`, `quiz`, `flashcards`, `dashboard`, `review`, `plan`, `import`, `help`.

### Direct commands
```bash
genai-tutor quiz              # Mixed quiz (10 questions)
genai-tutor quiz --domain 2   # Domain 2 only
genai-tutor quiz --count 20   # 20 questions
genai-tutor flashcards        # Due cards (spaced repetition)
genai-tutor flashcards --domain 3
genai-tutor dashboard         # Readiness score
genai-tutor review            # Drill weak areas
genai-tutor plan              # View study plan
genai-tutor plan --reset      # Reset all progress
genai-tutor import <url|file> # Import supplementary reading
genai-tutor import --list     # List imported content
genai-tutor import --delete 1 # Delete record by ID
genai-tutor help              # Exam info and tips
```

## Running Tests

```bash
pytest
```

## Readiness Score

The readiness score is a weighted composite:
- **Quiz accuracy** × 50%
- **Flashcard retention** × 30%
- **Study plan completion** × 20%

| Score | Status |
|-------|--------|
| ≥ 80% | READY — schedule your exam |
| ≥ 65% | LIKELY — a few more days of study |
| ≥ 50% | NEEDS WORK — focus on weak domains |
| < 50% | NOT READY — more study needed |

## Exam Details

- **Duration:** 90 minutes
- **Format:** 50-60 multiple choice
- **Fee:** $99 USD
- **Validity:** 3 years
- **No hands-on experience required** — business-level knowledge focus
