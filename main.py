import asyncio
import base64
import io
import json
import unicodedata
from datetime import date
from pathlib import Path

import flet as ft
import pytesseract
from PIL import Image, UnidentifiedImageError


DATA_FILE = Path.home() / ".test_strategy_learning.json"
WEAK_PROBLEMS_FILE = Path.home() / ".test_strategy_weak_problems.json"
GREEN = "#2E6654"
GREEN_LIGHT = "#E2EDE5"
PAPER = "#F6F5EF"
INK = "#202C2A"
MUTED = "#77807B"
CORAL = "#CF6048"
WHITE = "#FFFEFA"
MAX_PHOTO_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000

LESSONS = [
    {
        "id": "plan",
        "eyebrow": "01  PLAN",
        "title": "勉強の順番を決める",
        "summary": "全部を完璧にするより、点につながる順に取り組もう。",
        "detail": "テスト範囲を見たら、まず「出そう」「苦手」「すぐ解ける」に分けます。"
        "出そうで苦手なところから始めると、限られた時間を得点に変えやすくなります。",
        "steps": [
            "テスト範囲を小さな単元に分ける",
            "苦手な単元に印をつける",
            "今日やることをひとつだけ決める",
        ],
        "tip": "予定は詰め込みすぎず、見直しの時間も残しておこう。",
    },
    {
        "id": "active-recall",
        "eyebrow": "02  RETRIEVE",
        "title": "思い出す練習をする",
        "summary": "読むだけでなく、何も見ずに答えを取り出してみよう。",
        "detail": "教科書を閉じて、覚えたことを口に出す・書き出す練習が効果的です。"
        "思い出せなかったところこそ、次に復習するポイントです。",
        "steps": [
            "短い範囲を読んでから本を閉じる",
            "要点や公式を自分の言葉で書き出す",
            "答え合わせをして、抜けを確かめる",
        ],
        "tip": "答えを見ながら「わかったつもり」にならないのがコツ。",
    },
    {
        "id": "mistakes",
        "eyebrow": "03  REVIEW",
        "title": "間違いを得点に変える",
        "summary": "間違えた問題は、次の点数を伸ばすヒント。",
        "detail": "答えを写して終わりにせず、間違えた理由を見つけましょう。"
        "知識不足・読み違い・計算ミスなど、原因がわかると対策も決めやすくなります。",
        "steps": [
            "どこで間違えたかを一言で記録する",
            "正しい考え方を自分で説明する",
            "少し時間をあけて、もう一度解く",
        ],
        "tip": "同じ問題を解き直せたら、攻略できたサイン。",
    },
    {
        "id": "exam-day",
        "eyebrow": "04  TEST DAY",
        "title": "本番で時間を味方にする",
        "summary": "解ける問題から進めて、最後に見直す時間を作ろう。",
        "detail": "最初に問題全体を見て、時間配分をざっくり決めます。"
        "迷った問題に印をつけて先へ進めば、解ける問題を取りこぼしにくくなります。",
        "steps": [
            "開始したら問題全体と配点を確認する",
            "解ける問題から答えていく",
            "残り時間で印をつけた問題を見直す",
        ],
        "tip": "見直しでは、名前・単位・問題の条件もチェック。",
    },
]

QUIZ = [
    {
        "question": "間違えた問題を復習するとき、いちばん効果的なのは？",
        "options": [
            "答えを写して、すぐ次の問題へ進む",
            "間違えた理由を見つけて、時間をあけて解き直す",
            "同じページを何度も読む",
        ],
        "answer": 1,
        "explanation": "理由を知ってから解き直すと、次に同じミスを防ぎやすくなります。",
    },
    {
        "question": "テスト中、時間がかかりそうな問題に出会ったら？",
        "options": [
            "時間をかけてその場で解き切る",
            "空欄のままにして見直しもしない",
            "印をつけて先へ進み、あとで戻る",
        ],
        "answer": 2,
        "explanation": "解ける問題を先に取り、残り時間で戻ると得点の取りこぼしを減らせます。",
    },
    {
        "question": "覚えた内容が身についているか確かめるには？",
        "options": [
            "本を閉じて、覚えたことを自分で書き出す",
            "教科書を開いたまま何度も眺める",
            "ノートをきれいに書き直す",
        ],
        "answer": 0,
        "explanation": "何も見ずに思い出す練習で、覚えていることと復習が必要なことがわかります。",
    },
]


def extract_question_text(image_bytes):
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValueError("画像のサイズが大きすぎます。小さく撮影し直してください。")
        image = image.convert("L")
        text = pytesseract.image_to_string(image, lang="jpn+eng", config="--psm 6")
    return text.strip()


def normalize_answer(text):
    return "".join(unicodedata.normalize("NFKC", text).split()).casefold()


def load_weak_problems():
    try:
        data = json.loads(WEAK_PROBLEMS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], ""
    except (OSError, json.JSONDecodeError):
        return [], "苦手問題の保存データを読み込めません。"
    if not isinstance(data, list):
        return [], "苦手問題の保存データの形式が正しくありません。"
    problems = []
    for item in data:
        if (
            isinstance(item, dict)
            and all(isinstance(item.get(key), str) for key in ("question", "answer", "solution"))
            and isinstance(item.get("mistakes"), int)
            and item["mistakes"] > 0
        ):
            problems.append(item)
    return problems, ""


def load_progress():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set(), ""
    except (OSError, json.JSONDecodeError):
        return set(), "保存した進捗を読み込めませんでした。学習済み情報はこの起動中のみ保持されます。"
    if not isinstance(data, dict) or not isinstance(data.get("completed"), list):
        return set(), "保存データの形式が正しくありません。学習済み情報はこの起動中のみ保持されます。"
    lesson_ids = {lesson["id"] for lesson in LESSONS}
    completed = {
        item for item in data["completed"] if isinstance(item, str) and item in lesson_ids
    }
    return completed, ""


def main(page: ft.Page):
    page.title = "テスト攻略ラボ | 勉強のコツを学ぼう"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = PAPER
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    completed_lessons, storage_message = load_progress()
    weak_problems, weak_storage_message = load_weak_problems()
    selected_lesson_id = LESSONS[0]["id"]
    quiz_index = 0
    quiz_score = 0
    quiz_answered = False

    notice = ft.Text(
        storage_message,
        size=12,
        color=CORAL,
        visible=bool(storage_message),
    )
    progress_text = ft.Text(size=12, color=MUTED)
    progress_bar = ft.ProgressBar(
        value=0,
        color=GREEN,
        bgcolor=GREEN_LIGHT,
        height=6,
        border_radius=6,
    )
    lesson_buttons = ft.Column(spacing=8)
    lesson_detail = ft.Column(spacing=14)
    quiz_content = ft.Column(spacing=14)
    photo_status = ft.Text(
        "写真はこのアプリ内で読み取り、保存・送信しません。",
        size=12,
        color=MUTED,
    )
    photo_preview = ft.Image(
        src="",
        width=280,
        height=180,
        fit=ft.BoxFit.CONTAIN,
        visible=False,
    )
    question_text_input = ft.TextField(
        label="読み取った問題文（必要なら修正）",
        multiline=True,
        min_lines=3,
        max_lines=8,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
        visible=False,
    )
    answer_text_input = ft.TextField(
        label="模範解答（答え合わせに必要）",
        multiline=True,
        min_lines=1,
        max_lines=4,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
        visible=False,
    )
    solution_text_input = ft.TextField(
        label="解き方の解説（答え合わせの後に表示）",
        multiline=True,
        min_lines=2,
        max_lines=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
        visible=False,
    )
    photo_problem = ft.Column(spacing=12)
    photo_answer_input = ft.TextField(
        label="あなたの解答",
        multiline=True,
        min_lines=1,
        max_lines=4,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
    )
    photo_answer_feedback = ft.Text(size=13, visible=False)
    weak_status = ft.Text(
        weak_storage_message,
        size=12,
        color=CORAL,
        visible=bool(weak_storage_message),
    )
    weak_problem_list = ft.Column(spacing=10)
    active_problem = None
    answer_revealed = False
    answer_checked = False

    async def choose_photo(event):
        nonlocal active_problem, answer_revealed, answer_checked
        files = await photo_picker.pick_files(
            dialog_title="テスト問題の写真を選ぶ",
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False,
            with_data=True,
            compression_quality=85,
        )
        if not files:
            return
        selected = files[0]
        active_problem = None
        answer_revealed = False
        answer_checked = False
        photo_problem.controls = []
        photo_preview.visible = False
        question_text_input.visible = False
        answer_text_input.visible = False
        solution_text_input.visible = False
        make_photo_problem_button.visible = False
        if selected.bytes is None:
            photo_status.value = "画像データを読み込めませんでした。もう一度選んでください。"
            photo_status.color = CORAL
            page.update()
            return
        if len(selected.bytes) > MAX_PHOTO_BYTES:
            photo_status.value = "写真は12MB以下の画像を選んでください。"
            photo_status.color = CORAL
            page.update()
            return

        photo_preview.src_base64 = base64.b64encode(selected.bytes).decode("ascii")
        photo_preview.visible = True
        photo_status.value = "写真から問題文を読み取っています..."
        photo_status.color = MUTED
        page.update()

        try:
            recognized_text = await asyncio.to_thread(extract_question_text, selected.bytes)
        except pytesseract.TesseractNotFoundError:
            photo_status.value = "OCR機能が見つかりません。READMEのOCRセットアップ手順を確認してください。"
            photo_status.color = CORAL
            page.update()
            return
        except pytesseract.TesseractError as error:
            photo_status.value = f"日本語OCRに失敗しました: {error}"
            photo_status.color = CORAL
            page.update()
            return
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as error:
            photo_status.value = f"画像を読み取れませんでした: {error}"
            photo_status.color = CORAL
            page.update()
            return

        if not recognized_text:
            photo_status.value = "文字を読み取れませんでした。明るくピントの合った写真を撮ってください。"
            photo_status.color = CORAL
            page.update()
            return

        question_text_input.value = recognized_text
        question_text_input.visible = True
        answer_text_input.value = ""
        answer_text_input.visible = True
        solution_text_input.value = ""
        solution_text_input.visible = True
        make_photo_problem_button.visible = True
        photo_status.value = "読み取りました。問題文を確認・修正してから出題してください。"
        photo_status.color = GREEN
        page.update()

    def show_problem(event):
        nonlocal active_problem, answer_revealed, answer_checked
        question = (question_text_input.value or "").strip()
        if not question:
            photo_status.value = "問題文が空です。写真を撮り直すか、問題文を入力してください。"
            photo_status.color = CORAL
            page.update()
            return
        answer = (answer_text_input.value or "").strip()
        if not answer:
            photo_status.value = "答え合わせのため、模範解答を入力してください。"
            photo_status.color = CORAL
            page.update()
            return
        solution = (solution_text_input.value or "").strip()
        if not solution:
            photo_status.value = "答え合わせの後に解説を表示するため、解き方を入力してください。"
            photo_status.color = CORAL
            page.update()
            return
        active_problem = {
            "question": question,
            "answer": answer,
            "solution": solution,
        }
        answer_revealed = False
        answer_checked = False
        photo_answer_input.value = ""
        photo_answer_feedback.value = ""
        photo_answer_feedback.visible = False
        photo_status.value = "問題を出題しました。考えてから答えを確認しましょう。"
        photo_status.color = GREEN
        render_photo_problem()

    def check_photo_answer(event):
        nonlocal answer_revealed, answer_checked
        user_answer = (photo_answer_input.value or "").strip()
        if not user_answer:
            photo_answer_feedback.value = "解答を入力してから答え合わせしてください。"
            photo_answer_feedback.color = CORAL
            photo_answer_feedback.visible = True
            page.update()
            return
        answer_revealed = True
        answer_checked = True
        if normalize_answer(user_answer) == normalize_answer(active_problem["answer"]):
            photo_answer_feedback.value = "正解です！"
            photo_answer_feedback.color = GREEN
        else:
            photo_answer_feedback.value = "不正解です。模範解答を確認してみましょう。"
            photo_answer_feedback.color = CORAL
            record_weak_problem(active_problem)
        photo_answer_feedback.visible = True
        render_photo_problem()

    def save_weak_problems():
        try:
            WEAK_PROBLEMS_FILE.write_text(
                json.dumps(weak_problems, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            weak_status.value = f"苦手問題を保存できませんでした: {error}"
            weak_status.color = CORAL
            weak_status.visible = True
            return False
        weak_status.value = ""
        weak_status.visible = False
        return True

    def record_weak_problem(problem):
        key = normalize_answer(problem["question"])
        existing = next(
            (item for item in weak_problems if normalize_answer(item["question"]) == key),
            None,
        )
        if existing:
            existing["mistakes"] += 1
            existing["answer"] = problem["answer"]
            existing["solution"] = problem["solution"]
        else:
            weak_problems.append(
                {
                    "question": problem["question"],
                    "answer": problem["answer"],
                    "solution": problem["solution"],
                    "mistakes": 1,
                }
            )
        save_weak_problems()
        render_weak_problems()

    def mark_weak_problem_mastered(question):
        key = normalize_answer(question)
        weak_problems[:] = [
            item for item in weak_problems if normalize_answer(item["question"]) != key
        ]
        save_weak_problems()
        render_weak_problems()

    def render_weak_problems():
        weak_problem_list.controls = []
        if not weak_problems:
            weak_problem_list.controls.append(
                ft.Text("まだありません。問題を間違えると、ここに自動で追加されます。", size=13, color=MUTED)
            )
        else:
            for problem in sorted(
                weak_problems,
                key=lambda item: (-item["mistakes"], item["question"]),
            ):
                weak_problem_list.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            f"まちがい {problem['mistakes']} 回",
                                            size=11,
                                            color=CORAL,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Button(
                                            "克服した",
                                            on_click=lambda event, question=problem["question"]: mark_weak_problem_mastered(question),
                                            bgcolor=GREEN_LIGHT,
                                            color=GREEN,
                                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(problem["question"], size=14, color=INK, weight=ft.FontWeight.W_600),
                                ft.Text(f"模範解答：{problem['answer']}", size=12, color=MUTED),
                                ft.Text(f"解き方：{problem['solution']}", size=12, color=MUTED),
                            ],
                            spacing=8,
                        ),
                        padding=14,
                        bgcolor=WHITE,
                        border=ft.Border.all(1, "#E3E3D9"),
                        border_radius=8,
                    )
                )
        page.update()

    def reveal_answer(event):
        nonlocal answer_revealed
        answer_revealed = True
        render_photo_problem()

    def render_photo_problem():
        if not active_problem:
            photo_problem.controls = []
        else:
            photo_problem.controls = [
                ft.Text("出題中の問題", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Text(active_problem["question"], size=16, color=INK),
                    width=float("inf"),
                    padding=16,
                    bgcolor=WHITE,
                    border=ft.Border.all(1, "#E3E3D9"),
                    border_radius=8,
                ),
                photo_answer_input,
            ]
            if active_problem["answer"]:
                photo_problem.controls.extend(
                    [
                        ft.Text(
                            "模範解答と照合します（空白・全角半角の違いは無視）。",
                            size=11,
                            color=MUTED,
                        ),
                        ft.Button(
                            "答え合わせ",
                            on_click=check_photo_answer,
                            bgcolor=GREEN,
                            color="white",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                        ),
                        photo_answer_feedback,
                    ]
                )
                if answer_revealed:
                    photo_problem.controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("模範解答", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                                    ft.Text(active_problem["answer"], size=14, color=INK),
                                ],
                                spacing=6,
                            ),
                            padding=14,
                            bgcolor=GREEN_LIGHT,
                            border_radius=8,
                        )
                    )
                else:
                    photo_problem.controls.append(
                        ft.Button(
                            "模範解答を見る",
                            on_click=reveal_answer,
                            bgcolor=GREEN,
                            color="white",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                        )
                    )
            if answer_checked:
                photo_problem.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("解き方の解説", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                                ft.Text(active_problem["solution"], size=14, color=INK),
                            ],
                            spacing=6,
                        ),
                        padding=14,
                        bgcolor=GREEN_LIGHT,
                        border_radius=8,
                    )
                )
        page.update()

    photo_picker = ft.FilePicker()
    page.overlay.append(photo_picker)
    photo_picker_button = ft.Button(
        "写真を撮る / 画像を選ぶ",
        icon=ft.Icons.CAMERA_ALT_OUTLINED,
        on_click=choose_photo,
        bgcolor=GREEN,
        color="white",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
    )
    make_photo_problem_button = ft.Button(
        "この問題を出す",
        on_click=show_problem,
        bgcolor=GREEN,
        color="white",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
        visible=False,
    )

    def persist_progress():
        nonlocal storage_message
        try:
            DATA_FILE.write_text(
                json.dumps({"completed": sorted(completed_lessons)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            storage_message = ""
        except OSError:
            storage_message = "進捗を保存できませんでした。書き込み権限をご確認ください。"
        notice.value = storage_message
        notice.visible = bool(storage_message)

    def render_progress():
        count = len(completed_lessons)
        total = len(LESSONS)
        progress_text.value = f"{count} / {total} レッスン完了"
        progress_bar.value = count / total

    def select_lesson(lesson_id):
        nonlocal selected_lesson_id
        selected_lesson_id = lesson_id
        render_lessons()

    def toggle_completed(lesson_id):
        if lesson_id in completed_lessons:
            completed_lessons.remove(lesson_id)
        else:
            completed_lessons.add(lesson_id)
        persist_progress()
        render_progress()
        render_lessons()

    def render_lessons():
        lesson_buttons.controls = []
        for lesson in LESSONS:
            selected = lesson["id"] == selected_lesson_id
            done = lesson["id"] in completed_lessons
            lesson_buttons.controls.append(
                ft.Button(
                    content=ft.Row(
                        [
                            ft.Text("✓" if done else lesson["eyebrow"][:2], color=GREEN, size=13),
                            ft.Column(
                                [
                                    ft.Text(lesson["title"], color=INK, size=14, weight=ft.FontWeight.W_600),
                                    ft.Text("学習済み" if done else lesson["summary"], color=MUTED, size=11),
                                ],
                                spacing=3,
                                expand=True,
                            ),
                            ft.Text("›", color=GREEN if selected else MUTED, size=22),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    on_click=lambda event, item_id=lesson["id"]: select_lesson(item_id),
                    bgcolor=GREEN_LIGHT if selected else WHITE,
                    color=INK,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        side=ft.BorderSide(1, GREEN if selected else "#E3E3D9"),
                        padding=14,
                    ),
                )
            )

        lesson = next(item for item in LESSONS if item["id"] == selected_lesson_id)
        is_done = selected_lesson_id in completed_lessons
        lesson_detail.controls = [
            ft.Text(lesson["eyebrow"], size=11, color=GREEN, weight=ft.FontWeight.BOLD),
            ft.Text(lesson["title"], size=25, color=INK, weight=ft.FontWeight.W_600),
            ft.Text(lesson["detail"], size=14, color=MUTED),
            ft.Text("やってみよう", size=13, color=INK, weight=ft.FontWeight.BOLD),
        ]
        for index, step in enumerate(lesson["steps"], start=1):
            lesson_detail.controls.append(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(str(index), color=GREEN, size=12, weight=ft.FontWeight.BOLD),
                            width=24,
                            height=24,
                            bgcolor=GREEN_LIGHT,
                            border_radius=12,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(step, size=13, color=INK, expand=True),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        lesson_detail.controls.extend(
            [
                ft.Container(
                    content=ft.Text(f"ヒント  {lesson['tip']}", size=12, color=GREEN),
                    padding=12,
                    bgcolor=GREEN_LIGHT,
                    border_radius=6,
                ),
                ft.Button(
                    "学習済みにする" if not is_done else "学習済み ✓",
                    on_click=lambda event, item_id=selected_lesson_id: toggle_completed(item_id),
                    bgcolor=GREEN if not is_done else WHITE,
                    color="white" if not is_done else GREEN,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=6),
                        side=ft.BorderSide(1, GREEN),
                    ),
                ),
            ]
        )
        page.update()

    def answer_quiz(choice_index):
        nonlocal quiz_answered, quiz_score
        if quiz_answered:
            return
        question = QUIZ[quiz_index]
        is_correct = choice_index == question["answer"]
        quiz_answered = True
        if is_correct:
            quiz_score += 1
        render_quiz(
            "正解！ " + question["explanation"]
            if is_correct
            else "おしい！ " + question["explanation"],
            is_correct,
        )

    def next_question(event):
        nonlocal quiz_index, quiz_answered, quiz_score
        if quiz_index == len(QUIZ) - 1:
            quiz_index = 0
            quiz_answered = False
            quiz_score = 0
        else:
            quiz_index += 1
            quiz_answered = False
        render_quiz()

    def render_quiz(feedback="", is_correct=False):
        question = QUIZ[quiz_index]
        quiz_content.controls = [
            ft.Row(
                [
                    ft.Text(f"QUESTION {quiz_index + 1} / {len(QUIZ)}", size=11, color=GREEN, weight=ft.FontWeight.BOLD),
                    ft.Text(f"正解 {quiz_score} 問", size=11, color=MUTED),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Text(question["question"], size=17, color=INK, weight=ft.FontWeight.W_600),
        ]
        for index, option in enumerate(question["options"]):
            quiz_content.controls.append(
                ft.Button(
                    content=ft.Row(
                        [
                            ft.Text(chr(65 + index), size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                            ft.Text(option, size=13, color=INK, expand=True, text_align=ft.TextAlign.LEFT),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    on_click=lambda event, choice=index: answer_quiz(choice),
                    disabled=quiz_answered,
                    bgcolor=WHITE,
                    color=INK,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=6),
                        side=ft.BorderSide(1, "#E3E3D9"),
                        padding=14,
                    ),
                    width=float("inf"),
                )
            )
        if feedback:
            quiz_content.controls.append(
                ft.Container(
                    content=ft.Text(feedback, size=12, color=GREEN if is_correct else CORAL),
                    padding=12,
                    bgcolor=GREEN_LIGHT if is_correct else "#F9E9E4",
                    border_radius=6,
                )
            )
        if feedback:
            quiz_content.controls.append(
                ft.Button(
                    "もう一度挑戦" if quiz_index == len(QUIZ) - 1 else "次の問題へ",
                    on_click=next_question,
                    bgcolor=GREEN,
                    color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                )
            )
            if quiz_index == len(QUIZ) - 1:
                quiz_content.controls.append(
                    ft.Text(
                        f"今回の結果：{quiz_score} / {len(QUIZ)} 問正解",
                        size=12,
                        color=MUTED,
                    )
                )

    today = ft.Text(
        date.today().strftime("%Y年%m月%d日"),
        size=12,
        color=MUTED,
    )
    header = ft.Row(
        [
            ft.Row(
                [
                    ft.Container(
                        content=ft.Text("学", color="white", size=15, weight=ft.FontWeight.BOLD),
                        width=30,
                        height=30,
                        bgcolor=GREEN,
                        border_radius=15,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text("TEST SMART", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            today,
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    content = ft.Column(
        [
            header,
            ft.Column(
                [
                    ft.Text("テストは、コツで変わる。", size=34, color=INK, weight=ft.FontWeight.W_600),
                    ft.Text("勉強の進め方から本番の時間術まで、得点につながる攻略法を学ぼう。", size=13, color=MUTED),
                ],
                spacing=6,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("あなたの攻略メーター", size=13, color=INK, weight=ft.FontWeight.W_600),
                                progress_text,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        progress_bar,
                    ],
                    spacing=10,
                ),
                padding=18,
                bgcolor=WHITE,
                border=ft.Border.all(1, "#E3E3D9"),
                border_radius=8,
            ),
            notice,
            ft.Text("攻略レッスン", size=20, color=INK, weight=ft.FontWeight.W_600),
            ft.Column(
                [
                    ft.Container(content=lesson_buttons, width=300),
                    ft.Container(
                        content=lesson_detail,
                        padding=20,
                        bgcolor=WHITE,
                        border=ft.Border.all(1, "#E3E3D9"),
                        border_radius=8,
                    ),
                ],
                spacing=14,
            ),
            ft.Text("過去問を写真から出題", size=20, color=INK, weight=ft.FontWeight.W_600),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "問題を撮影するか画像を選ぶと、日本語OCRで問題文を読み取ります。"
                            "読み取り結果は修正できます。",
                            size=12,
                            color=MUTED,
                        ),
                        ft.Text(
                            "スマートフォンでは画像選択画面からカメラを選べます。写真は保存・送信されません。",
                            size=11,
                            color=MUTED,
                        ),
                        photo_picker_button,
                        photo_status,
                        photo_preview,
                        question_text_input,
                        answer_text_input,
                        solution_text_input,
                        make_photo_problem_button,
                        ft.Divider(height=1, color="#E3E3D9"),
                        photo_problem,
                    ],
                    spacing=12,
                ),
                padding=20,
                bgcolor=WHITE,
                border=ft.Border.all(1, "#E3E3D9"),
                border_radius=8,
            ),
            ft.Text("苦手問題ノート", size=20, color=INK, weight=ft.FontWeight.W_600),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "間違えた写真問題を自動で記録します。解き方を見直し、理解できたら「克服した」を押しましょう。",
                            size=12,
                            color=MUTED,
                        ),
                        weak_status,
                        weak_problem_list,
                    ],
                    spacing=12,
                ),
                padding=20,
                bgcolor=WHITE,
                border=ft.Border.all(1, "#E3E3D9"),
                border_radius=8,
            ),
            ft.Row(
                [
                    ft.Text("実践クイズ", size=20, color=INK, weight=ft.FontWeight.W_600),
                    ft.Text("学んだコツを試そう", size=12, color=MUTED),
                ],
                spacing=10,
            ),
            ft.Container(
                content=quiz_content,
                padding=20,
                bgcolor=WHITE,
                border=ft.Border.all(1, "#E3E3D9"),
                border_radius=8,
            ),
            ft.Text("小さな工夫を、次の自信に。", size=12, color=MUTED, text_align=ft.TextAlign.CENTER),
        ],
        width=760,
        spacing=20,
    )
    app_container = ft.Container(content=content, width=760, padding=ft.Padding.only(top=18, bottom=32))

    def resize_page(event):
        viewport_width = page.width or 808
        page.padding = 12 if viewport_width < 520 else 24
        content_width = min(760, max(272, viewport_width - page.padding * 2))
        app_container.width = content_width
        content.width = content_width
        lesson_list_panel = content.controls[5].controls[0]
        lesson_list_panel.width = min(300, content_width)
        page.update()

    page.on_resize = resize_page
    page.add(app_container)
    render_progress()
    render_lessons()
    render_weak_problems()
    render_quiz()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
