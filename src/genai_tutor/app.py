"""Main CLI application for the GCP Generative AI Leader Tutor."""

from __future__ import annotations

import textwrap
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from genai_tutor.db import init_db
from genai_tutor.seed import seed_all
import genai_tutor.quiz as quiz_engine
import genai_tutor.flashcards as fc_engine
import genai_tutor.study as study_engine
from genai_tutor.dashboard import get_dashboard_data
from genai_tutor.review import get_weak_domains, get_weak_subtopics, get_all_domains, get_all_subtopics

console = Console(stderr=False)
app = typer.Typer(
    name="genai-tutor",
    help="GCP Generative AI Leader Certification Study Tool",
    add_completion=False,
)

DOMAIN_COLORS = {1: "cyan", 2: "green", 3: "yellow", 4: "magenta"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_header(title: str, subtitle: str = "") -> None:
    text = Text(title, style="bold white")
    if subtitle:
        text.append(f"\n{subtitle}", style="dim")
    console.print(Panel(text, border_style="blue", expand=False))


def _print_success(msg: str) -> None:
    console.print(f"[bold green]✓[/bold green] {msg}")


def _print_error(msg: str) -> None:
    console.print(f"[bold red]✗[/bold red] {msg}")


def _prompt_continue() -> None:
    try:
        console.input("\n[dim]Press Enter to continue...[/dim]")
    except EOFError:
        pass


def _wrap(text: str, width: int = 88) -> str:
    return "\n".join(textwrap.fill(line, width) if line else "" for line in text.split("\n"))


def _readiness_style(label: str) -> str:
    return {"READY": "bold green", "LIKELY": "bold yellow", "NEEDS WORK": "bold red", "NOT READY": "bold red"}.get(label, "white")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def _show_main_menu() -> None:
    console.clear()
    _print_header(
        "GCP Generative AI Leader Tutor",
        "Certification exam preparation tool",
    )
    console.print()
    console.print("[bold cyan]Commands:[/bold cyan]")
    console.print("  [bold]study[/bold]      - Today's structured study session (reading + flashcards + quiz)")
    console.print("  [bold]quiz[/bold]       - Take a practice quiz")
    console.print("  [bold]flashcards[/bold] - Review spaced-repetition flashcards")
    console.print("  [bold]dashboard[/bold]  - View your readiness score and progress")
    console.print("  [bold]review[/bold]     - Drill your weak areas")
    console.print("  [bold]plan[/bold]       - View or reset your 28-day study plan")
    console.print("  [bold]help[/bold]       - Show exam information and tips")
    console.print("  [bold]quit[/bold]       - Exit")
    console.print()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """GCP Generative AI Leader Certification Study Tool."""
    init_db()
    seed_all()

    if ctx.invoked_subcommand is not None:
        return

    # Interactive REPL mode
    while True:
        _show_main_menu()
        cmd = console.input("[bold]> [/bold]").strip().lower()
        if cmd in ("quit", "exit", "q"):
            console.print("\n[bold]Good luck with your certification![/bold]")
            raise typer.Exit()
        elif cmd == "study":
            _run_study_session()
        elif cmd == "quiz":
            _run_quiz_interactive()
        elif cmd in ("flashcards", "fc"):
            _run_flashcards_interactive()
        elif cmd == "dashboard":
            _run_dashboard()
        elif cmd == "review":
            _run_review()
        elif cmd == "plan":
            _run_plan()
        elif cmd == "help":
            _run_help()
        elif cmd == "":
            continue
        else:
            _print_error(f"Unknown command: '{cmd}'. Type 'help' for options.")
            _prompt_continue()


# ---------------------------------------------------------------------------
# Study session
# ---------------------------------------------------------------------------

@app.command()
def study() -> None:
    """Start today's structured study session (reading + flashcards + quiz)."""
    init_db()
    seed_all()
    _run_study_session()


def _run_study_session() -> None:
    day_num = study_engine.get_current_day()
    day = study_engine.get_study_day(day_num)
    if day is None:
        console.print("[bold green]You have completed all study days! Use 'review' or 'quiz' to keep practising.[/bold green]")
        _prompt_continue()
        return

    progress = study_engine.ensure_progress(day.id)
    console.clear()
    _print_header(f"Day {day.day_number} Study Session", "Reading  ->  Flashcards  ->  Quiz")

    # --- READING ---
    if not progress.reading_complete:
        console.print(f"\n[bold cyan]READING[/bold cyan]")
        console.print(Panel(_wrap(day.reading_content), title="Study Material", border_style="cyan"))
        try:
            ans = console.input("\n[dim]Mark reading as complete? (y/n)[/dim]: ").strip().lower()
        except EOFError:
            ans = "n"
        if ans == "y":
            study_engine.mark_reading_complete(day.id)
            _print_success("Reading complete!")
        else:
            console.print("[dim]Reading skipped — you can return to it tomorrow.[/dim]")
            _prompt_continue()
            return
    else:
        console.print("[dim]Reading already complete for today.[/dim]")

    # --- FLASHCARDS ---
    if not progress.flashcard_complete:
        console.print(f"\n[bold yellow]FLASHCARDS[/bold yellow]")
        cards = fc_engine.get_cards_for_domain(day.domain_id, limit=10)
        if not cards:
            cards = fc_engine.get_due_cards(limit=10)
        if cards:
            score = _run_flashcard_session(cards)
            study_engine.mark_flashcards_complete(day.id)
            _print_success(f"Flashcards complete! ({score})")
        else:
            console.print("[dim]No flashcards available.[/dim]")
            study_engine.mark_flashcards_complete(day.id)
    else:
        console.print("[dim]Flashcards already complete for today.[/dim]")

    # --- QUIZ ---
    if not progress.quiz_complete:
        console.print(f"\n[bold magenta]QUIZ[/bold magenta]")
        questions = quiz_engine.get_questions_by_domain(day.domain_id, count=8)
        if not questions:
            questions = quiz_engine.get_random_questions(count=8)
        correct, total = _run_quiz_session(questions)
        study_engine.mark_quiz_complete(day.id)
        pct = correct / total * 100 if total else 0
        _print_success(f"Quiz complete! Score: {correct}/{total} ({pct:.0f}%)")
    else:
        console.print("[dim]Quiz already complete for today.[/dim]")

    console.print(f"\n[bold green]Day {day.day_number} complete![/bold green]")
    completed = study_engine.get_completed_days()
    total_days = study_engine.get_total_days()
    console.print(f"Progress: {completed}/{total_days} days")
    _prompt_continue()


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

@app.command()
def quiz(
    domain: int = typer.Option(0, "--domain", "-d", help="Domain ID (1-4), 0=all"),
    count: int = typer.Option(10, "--count", "-n", help="Number of questions"),
) -> None:
    """Take a practice quiz."""
    init_db()
    seed_all()
    _run_quiz_interactive(domain_id=domain, count=count)


def _run_quiz_interactive(domain_id: int = 0, count: int = 0) -> None:
    console.clear()
    if count == 0:
        count = 10

    if domain_id == 0:
        domain_id = _select_domain_or_all()

    if domain_id == 0:
        questions = quiz_engine.get_random_questions(count)
        title = "Mixed Quiz"
    else:
        questions = quiz_engine.get_questions_by_domain(domain_id, count)
        domains = get_all_domains()
        domain_name = next((d["name"] for d in domains if d["id"] == domain_id), f"Domain {domain_id}")
        title = f"Domain {domain_id}: {domain_name}"

    if not questions:
        _print_error("No questions found for the selected filter.")
        _prompt_continue()
        return

    _print_header(title, f"{len(questions)} questions")
    correct, total = _run_quiz_session(questions)
    pct = correct / total * 100 if total else 0
    console.print(f"\n[bold]Final Score: {correct}/{total} ({pct:.0f}%)[/bold]")
    if pct >= 80:
        console.print("[bold green]Excellent! You're on track for the exam.[/bold green]")
    elif pct >= 65:
        console.print("[bold yellow]Good effort! Keep reviewing the areas you missed.[/bold yellow]")
    else:
        console.print("[bold red]Keep studying! Use 'review' to focus on weak areas.[/bold red]")
    _prompt_continue()


def _run_quiz_session(questions) -> tuple[int, int]:
    correct_count = 0
    for i, q in enumerate(questions, 1):
        console.print(f"\n[bold]Question {i}/{len(questions)}[/bold]")
        console.print(Panel(_wrap(q.stem), border_style="white"))
        console.print(f"  [cyan]a)[/cyan] {q.choice_a}")
        console.print(f"  [cyan]b)[/cyan] {q.choice_b}")
        console.print(f"  [cyan]c)[/cyan] {q.choice_c}")
        console.print(f"  [cyan]d)[/cyan] {q.choice_d}")

        while True:
            try:
                ans = console.input("\n[bold]Your answer (a/b/c/d) or 'q' to quit quiz: [/bold]").strip().lower()
            except EOFError:
                ans = "q"
            if ans in ("a", "b", "c", "d", "q"):
                break
            console.print("[dim]Please enter a, b, c, or d.[/dim]")

        if ans == "q":
            break

        is_correct = quiz_engine.record_answer(q.id, ans, q.correct_answer)
        if is_correct:
            correct_count += 1
            _print_success("Correct!")
        else:
            _print_error(f"Incorrect. The correct answer was: [bold]{q.correct_answer}[/bold]")

        console.print(f"\n[dim italic]{_wrap(q.explanation)}[/dim italic]")

    return correct_count, len(questions)


def _select_domain_or_all() -> int:
    """Prompt user to pick a domain or 0 for all."""
    domains = get_all_domains()
    console.print("\n[bold]Select domain:[/bold]")
    console.print("  [cyan]0)[/cyan] All domains (mixed)")
    for d in domains:
        console.print(f"  [cyan]{d['id']})[/cyan] Domain {d['section_number']}: {d['name']} ({d['exam_weight']:.0f}%)")

    while True:
        try:
            val = console.input("\nDomain [0-4]: ").strip()
        except EOFError:
            return 0
        if val.isdigit() and int(val) in range(5):
            return int(val)
        console.print("[dim]Please enter 0, 1, 2, 3, or 4.[/dim]")


# ---------------------------------------------------------------------------
# Flashcards
# ---------------------------------------------------------------------------

@app.command()
def flashcards(
    domain: int = typer.Option(0, "--domain", "-d", help="Domain ID (1-4), 0=due cards"),
) -> None:
    """Review spaced-repetition flashcards."""
    init_db()
    seed_all()
    _run_flashcards_interactive(domain_id=domain)


def _run_flashcards_interactive(domain_id: int = 0) -> None:
    console.clear()
    if domain_id == 0:
        cards = fc_engine.get_due_cards(limit=15)
        title = "Due Flashcards"
    else:
        cards = fc_engine.get_cards_for_domain(domain_id, limit=15)
        domains = get_all_domains()
        domain_name = next((d["name"] for d in domains if d["id"] == domain_id), f"Domain {domain_id}")
        title = f"Domain {domain_id}: {domain_name}"

    if not cards:
        console.print("[bold green]No flashcards due for review right now! Come back tomorrow.[/bold green]")
        _prompt_continue()
        return

    _print_header(title, f"{len(cards)} cards to review")
    score = _run_flashcard_session(cards)
    console.print(f"\n[bold]Flashcard session complete![/bold] {score}")
    _prompt_continue()


def _run_flashcard_session(cards) -> str:
    total = len(cards)
    good_count = 0
    for i, card in enumerate(cards, 1):
        console.clear()
        console.print(f"[dim]Card {i}/{total}[/dim]\n")
        console.print(Panel(_wrap(card.front), title="FRONT", border_style="yellow"))
        try:
            console.input("[dim]Press Enter to reveal answer...[/dim]")
        except EOFError:
            pass
        console.print(Panel(_wrap(card.back), title="BACK", border_style="green"))

        console.print("\n[bold]How well did you recall this?[/bold]")
        console.print("  [red]0[/red] - Complete blackout")
        console.print("  [red]1[/red] - Incorrect, but answer feels familiar")
        console.print("  [yellow]2[/yellow] - Incorrect, but the answer was easy to recall when seen")
        console.print("  [yellow]3[/yellow] - Correct, but with significant difficulty")
        console.print("  [green]4[/green] - Correct, with hesitation")
        console.print("  [green]5[/green] - Perfect recall")

        while True:
            try:
                val = console.input("\nRating (0-5): ").strip()
            except EOFError:
                val = "3"
            if val.isdigit() and int(val) in range(6):
                quality = int(val)
                break
            console.print("[dim]Please enter a number from 0 to 5.[/dim]")

        fc_engine.record_flashcard_result(card, quality)
        if quality >= 3:
            good_count += 1

    return f"{good_count}/{total} recalled well (rated ≥3)"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.command()
def dashboard() -> None:
    """View your readiness score and progress breakdown."""
    init_db()
    seed_all()
    _run_dashboard()


def _run_dashboard() -> None:
    console.clear()
    data = get_dashboard_data()
    score = data["readiness_score"]
    label = data["readiness_label"]
    label_style = _readiness_style(label)

    _print_header("Readiness Dashboard", "GCP Generative AI Leader")

    # Overall score panel
    score_text = Text()
    score_text.append(f"\n  Readiness Score: ", style="bold")
    score_text.append(f"{score:.1f}%", style="bold white")
    score_text.append(f"  |  Status: ", style="bold")
    score_text.append(f"{label}", style=label_style)
    score_text.append(f"\n\n  Quiz Accuracy:        {data['quiz_accuracy']:.1f}%", style="cyan")
    score_text.append(f"\n  Flashcard Retention:  {data['flashcard_retention']:.1f}%", style="yellow")
    score_text.append(f"\n  Study Completion:     {data['study_completion_pct']:.1f}%", style="green")
    score_text.append(f"\n  Days Completed:       {data['days_completed']}/{data['total_days']}", style="white")
    score_text.append(f"\n  Total Quiz Answers:   {data['total_quizzes']}", style="white")
    score_text.append(f"\n  Flashcards Reviewed:  {data['total_flashcards']}", style="white")
    console.print(Panel(score_text, border_style=label_style.split()[-1]))

    # Domain breakdown
    if data["domain_scores"]:
        console.print("\n[bold]Domain Performance:[/bold]")
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Domain", style="white", no_wrap=True)
        table.add_column("Accuracy", justify="right")
        table.add_column("Questions Answered", justify="right")
        table.add_column("Status", justify="center")

        for domain_id, ds in sorted(data["domain_scores"].items()):
            acc = ds["accuracy"]
            status = "[green]Good[/green]" if acc >= 70 else "[yellow]Review[/yellow]" if acc >= 50 else "[red]Weak[/red]"
            table.add_row(
                f"D{domain_id}: {ds['name'][:40]}",
                f"{acc:.1f}%",
                str(ds["total"]),
                status,
            )
        console.print(table)
    else:
        console.print("\n[dim]No quiz results yet. Take some quizzes to see domain breakdown.[/dim]")

    # Progress bar
    pct = data["study_completion_pct"]
    bar_width = 40
    filled = int(bar_width * pct / 100)
    bar = "\[" + "#" * filled + "-" * (bar_width - filled) + "]"
    console.print(f"\nStudy Plan: {bar} {pct:.0f}%")

    _prompt_continue()


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

@app.command()
def review() -> None:
    """Drill your weakest areas with targeted quizzes."""
    init_db()
    seed_all()
    _run_review()


def _run_review() -> None:
    console.clear()
    _print_header("Weak Area Review", "Targeted practice on low-scoring topics")

    weak_domains = get_weak_domains(threshold=70.0)
    weak_subtopics = get_weak_subtopics(threshold=70.0)

    if not weak_domains and not weak_subtopics:
        console.print("\n[bold green]No weak areas detected! You're scoring above 70% everywhere.[/bold green]")
        console.print("Try a full mixed quiz to stay sharp.")
        _prompt_continue()
        return

    if weak_subtopics:
        console.print("\n[bold red]Weakest Subtopics:[/bold red]")
        for i, st in enumerate(weak_subtopics[:5], 1):
            console.print(f"  {i}. {st['name']} ({st['domain_name']}) — {st['accuracy']:.0f}% ({st['total']} Qs)")

    if weak_domains:
        console.print("\n[bold yellow]Weak Domains:[/bold yellow]")
        for d in weak_domains:
            console.print(f"  Domain {d['domain_id']}: {d['name']} — {d['accuracy']:.0f}%")

    console.print("\n[bold]Drill options:[/bold]")
    console.print("  [cyan]1)[/cyan] Quiz on weakest subtopic")
    console.print("  [cyan]2)[/cyan] Quiz on weakest domain")
    console.print("  [cyan]3)[/cyan] Flashcards on weakest domain")
    console.print("  [cyan]q)[/cyan] Back to menu")

    try:
        choice = console.input("\nSelect: ").strip().lower()
    except EOFError:
        choice = "q"

    if choice == "1" and weak_subtopics:
        st = weak_subtopics[0]
        questions = quiz_engine.get_questions_by_subtopic(st["subtopic_id"], count=10)
        if not questions:
            _print_error(f"No quiz questions found for subtopic: {st['name']}")
        else:
            console.print(f"\n[bold]Drilling: {st['name']}[/bold]")
            correct, total = _run_quiz_session(questions)
            pct = correct / total * 100 if total else 0
            console.print(f"\nScore: {correct}/{total} ({pct:.0f}%)")

    elif choice == "2" and weak_domains:
        d = weak_domains[0]
        questions = quiz_engine.get_questions_by_domain(d["domain_id"], count=10)
        if not questions:
            _print_error(f"No questions found for domain: {d['name']}")
        else:
            console.print(f"\n[bold]Drilling Domain: {d['name']}[/bold]")
            correct, total = _run_quiz_session(questions)
            pct = correct / total * 100 if total else 0
            console.print(f"\nScore: {correct}/{total} ({pct:.0f}%)")

    elif choice == "3" and weak_domains:
        d = weak_domains[0]
        cards = fc_engine.get_cards_for_domain(d["domain_id"], limit=12)
        if not cards:
            _print_error(f"No flashcards found for domain: {d['name']}")
        else:
            console.print(f"\n[bold]Flashcards: {d['name']}[/bold]")
            _run_flashcard_session(cards)

    elif choice != "q":
        console.print("[dim]No action taken.[/dim]")

    _prompt_continue()


# ---------------------------------------------------------------------------
# Study plan
# ---------------------------------------------------------------------------

@app.command()
def plan(
    reset: bool = typer.Option(False, "--reset", help="Reset all progress"),
) -> None:
    """View or reset your 28-day study plan."""
    init_db()
    seed_all()
    _run_plan(do_reset=reset)


def _run_plan(do_reset: bool = False) -> None:
    console.clear()
    _print_header("28-Day Study Plan", "GCP Generative AI Leader")

    if do_reset:
        confirm = console.input("[bold red]This will reset ALL quiz results, flashcard progress, and study completion. Are you sure? (yes/no): [/bold red]").strip().lower()
        if confirm == "yes":
            study_engine.reset_progress()
            _print_success("All progress reset.")
        else:
            console.print("[dim]Reset cancelled.[/dim]")
        _prompt_continue()
        return

    completed = study_engine.get_completed_days()
    total = study_engine.get_total_days()
    current = study_engine.get_current_day()

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Day", justify="right", style="dim", width=4)
    table.add_column("Domain")
    table.add_column("Status", justify="center", width=12)

    with __import__("genai_tutor.db", fromlist=["get_connection"]).get_connection() as conn:
        rows = conn.execute(
            """SELECT sd.day_number, sd.domain_id, d.name,
                      up.reading_complete, up.flashcard_complete, up.quiz_complete
               FROM study_days sd
               JOIN domains d ON sd.domain_id = d.id
               LEFT JOIN user_progress up ON sd.id = up.study_day_id
               ORDER BY sd.day_number"""
        ).fetchall()

    for row in rows:
        day_num = row["day_number"]
        r, fc, q = row["reading_complete"], row["flashcard_complete"], row["quiz_complete"]
        if r and fc and q:
            status = "[green]Done[/green]"
        elif day_num == current:
            status = "[yellow]Today[/yellow]"
        elif r or fc or q:
            status = "[yellow]Partial[/yellow]"
        else:
            status = "[dim]Pending[/dim]"

        table.add_row(
            str(day_num),
            f"D{row['domain_id']}: {row['name']}",
            status,
        )

    console.print(table)
    console.print(f"\nCompleted: {completed}/{total} days")
    console.print(f"Current day: {current}")
    console.print("\n[dim]Run with --reset to start over.[/dim]")
    _prompt_continue()


# ---------------------------------------------------------------------------
# Help / Exam info
# ---------------------------------------------------------------------------

@app.command(name="help")
def help_cmd() -> None:
    """Show exam information and study tips."""
    init_db()
    seed_all()
    _run_help()


def _run_help() -> None:
    console.clear()
    _print_header("GCP Generative AI Leader — Exam Info")

    console.print(Panel(
        """[bold]Exam Format[/bold]
  • Duration:   90 minutes
  • Questions:  50-60 multiple choice
  • Fee:        $99 USD
  • Validity:   3 years
  • Delivery:   Online or onsite proctored
  • Languages:  English, Japanese

[bold]Exam Domains & Weights[/bold]
  [cyan]D1[/cyan] Fundamentals of Generative AI            30%
  [green]D2[/green] Google Cloud Gen AI Products & Strategy  35%
  [yellow]D3[/yellow] Techniques to Improve Gen AI Output      20%
  [magenta]D4[/magenta] Business Strategies for AI Adoption      15%

[bold]Official Resources[/bold]
  • Certification page: cloud.google.com/learn/certification/generative-ai-leader
  • Learning path:      cloudskillsboost.google/paths/1951
  • Exam guide:         services.google.com/fh/files/misc/generative_ai_leader_exam_guide_english.pdf

[bold]Study Tips[/bold]
  1. Aim for 80%+ readiness score before sitting the exam
  2. Focus extra time on Domain 2 (highest weight: 35%)
  3. Use spaced repetition flashcards daily — don't skip!
  4. After each quiz, read all explanations (not just wrong ones)
  5. Drill weak areas using 'review' before the exam
  6. This is a business-level exam — no coding or labs required""",
        border_style="blue",
    ))
    _prompt_continue()
