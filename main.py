import asyncio
import base64
from collections import Counter
import io
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

import flet as ft
import pytesseract
from PIL import Image, UnidentifiedImageError


DATA_FILE = Path.home() / ".test_strategy_learning.json"
WEAK_PROBLEMS_FILE = Path.home() / ".test_strategy_weak_problems.json"
PAST_QUESTIONS_FILE = Path.home() / ".test_strategy_past_questions.json"
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

HIGH_SCHOOL_CURRICULUM = {
    "1": {
        "国語": (
            "現代の国語：論理的な文章",
            "現代の国語：実用的な文章",
            "言語文化：古文の基礎",
            "言語文化：漢文の基礎",
        ),
        "地理歴史": (
            "地理総合：地図とGIS",
            "地理総合：生活文化と地域",
            "地理総合：自然環境と防災",
            "歴史総合：近代化と世界",
            "歴史総合：大衆化と戦争",
            "歴史総合：グローバル化",
        ),
        "公民": (
            "公共：青年期と自己形成",
            "公共：社会参加と合意形成",
            "公共：政治参加と選挙",
            "公共：経済と労働",
            "公共：国際社会と平和",
        ),
        "数学": (
            "数学I：数と式",
            "数学I：図形と計量",
            "数学I：二次関数",
            "数学I：データの分析",
            "数学A：場合の数と確率",
            "数学A：図形の性質",
            "数学A：数学と人間の活動",
        ),
        "理科": (
            "物理基礎：運動とエネルギー",
            "物理基礎：波",
            "化学基礎：物質の構成",
            "化学基礎：物質の変化",
            "生物基礎：生物の特徴",
            "生物基礎：遺伝子と生物の体内環境",
            "地学基礎：地球とその活動",
            "地学基礎：大気と宇宙",
        ),
        "英語": (
            "英語コミュニケーションI：聞く・話す",
            "英語コミュニケーションI：読む・書く",
            "論理・表現I：文法と表現",
            "論理・表現I：スピーチとライティング",
        ),
        "情報": (
            "情報I：情報社会と問題解決",
            "情報I：情報デザイン",
            "情報I：プログラミング",
            "情報I：ネットワークとデータ活用",
        ),
        "保健体育": ("保健：現代社会と健康", "体育：体つくりと運動"),
        "家庭": ("家庭基礎：生活設計", "家庭基礎：食生活", "家庭基礎：衣生活と住生活"),
        "芸術": ("音楽I：表現と鑑賞", "美術I：表現と鑑賞", "書道I：表現と鑑賞"),
    },
    "2": {
        "国語": (
            "論理国語：論理的な文章",
            "文学国語：文学的な文章",
            "古典探究：古文",
            "古典探究：漢文",
        ),
        "地理歴史": (
            "地理探究：自然環境と資源",
            "地理探究：産業と人口",
            "地理探究：地域調査",
            "日本史探究：原始・古代",
            "日本史探究：中世・近世",
            "世界史探究：諸地域の歴史",
            "世界史探究：近現代の世界",
        ),
        "公民": (
            "倫理：人間としての在り方生き方",
            "政治・経済：民主政治と法",
            "政治・経済：経済活動と福祉",
            "政治・経済：国際政治と国際経済",
        ),
        "数学": (
            "数学II：いろいろな式",
            "数学II：図形と方程式",
            "数学II：三角関数",
            "数学II：指数関数・対数関数",
            "数学II：微分・積分",
            "数学B：数列",
            "数学B：統計的な推測",
            "数学C：ベクトル",
        ),
        "理科": (
            "物理：力学",
            "物理：波動",
            "化学：物質の状態と変化",
            "化学：物質の反応",
            "生物：生命現象と物質",
            "生物：遺伝情報と生物の進化",
            "地学：地球の活動と歴史",
            "地学：大気・海洋と宇宙",
        ),
        "英語": (
            "英語コミュニケーションII：聞く・話す",
            "英語コミュニケーションII：読む・書く",
            "論理・表現II：文法と論理構成",
            "論理・表現II：発表とライティング",
        ),
        "情報": ("情報I：プログラミング", "情報I：ネットワークとデータ活用", "情報II：情報システム"),
        "保健体育": ("保健：安全な社会生活", "体育：運動とスポーツ"),
        "家庭": ("家庭総合：子どもと家庭", "家庭総合：高齢者と福祉", "家庭総合：消費生活"),
        "芸術": ("音楽II：表現と鑑賞", "美術II：表現と鑑賞", "書道II：表現と鑑賞"),
    },
    "3": {
        "国語": (
            "論理国語：論理的な文章",
            "文学国語：文学的な文章",
            "古典探究：古文",
            "古典探究：漢文",
            "国語表現：小論文と実用文",
        ),
        "地理歴史": (
            "地理探究：自然環境と資源",
            "地理探究：産業と人口",
            "地理探究：地域調査",
            "日本史探究：原始から近世",
            "日本史探究：近現代の日本",
            "世界史探究：諸地域の歴史",
            "世界史探究：近現代の世界",
        ),
        "公民": (
            "倫理：現代の倫理的課題",
            "政治・経済：民主政治と法",
            "政治・経済：経済活動と福祉",
            "政治・経済：国際政治と国際経済",
        ),
        "数学": (
            "数学III：極限",
            "数学III：微分法",
            "数学III：積分法",
            "数学B：数列",
            "数学B：統計的な推測",
            "数学C：ベクトル",
            "数学C：平面上の曲線と複素数平面",
        ),
        "理科": (
            "物理：力学・波動",
            "物理：電磁気・原子",
            "化学：物質の状態と反応",
            "化学：無機物質・有機化合物",
            "生物：生命現象と遺伝情報",
            "生物：生態系と進化",
            "地学：地球の活動と歴史",
            "地学：大気・海洋と宇宙",
        ),
        "英語": (
            "英語コミュニケーションIII：聞く・話す",
            "英語コミュニケーションIII：読む・書く",
            "論理・表現III：論理構成と発表",
            "論理・表現III：ディベートとライティング",
        ),
        "情報": ("情報I：情報社会と問題解決", "情報I：プログラミング", "情報II：データサイエンス"),
        "保健体育": ("保健：生涯を通じる健康", "保健：健康を支える環境", "体育：運動とスポーツ"),
        "家庭": ("家庭総合：生活設計と福祉", "家庭総合：消費生活と環境"),
        "芸術": ("音楽III：表現と鑑賞", "美術III：表現と鑑賞", "書道III：表現と鑑賞"),
    },
}

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


def topic_matches_subject(topic, subject):
    topic_key = normalize_answer(topic)
    subject_key = normalize_answer(subject)
    return topic_key == subject_key or any(
        topic_key.startswith(subject_key + separator)
        for separator in ("・", ":", "-", "/", "_", "(")
    )


def topic_scope_label(topic, subject):
    if topic_matches_subject(topic, subject):
        if normalize_answer(topic) == normalize_answer(subject):
            return "単元未設定"
        for separator in ("・", ":", "-", "/", "_", "("):
            prefix = f"{subject}{separator}"
            if topic.casefold().startswith(prefix.casefold()):
                return topic[len(prefix):].strip() or "単元未設定"
    return topic


QUESTION_FORMATS = (
    ("計算・数値", re.compile(r"計算|求め|解け|値を|何cm|何％")),
    ("説明・理由", re.compile(r"説明|述べ|理由|なぜ|書きなさい")),
    ("選択", re.compile(r"選び|選択|記号|適切なもの|正しいもの")),
    ("グラフ・作図", re.compile(r"グラフ|作図|描き|図に")),
    ("語句・穴埋め", re.compile(r"語句|空欄|穴埋め|埋めなさい")),
    ("証明", re.compile(r"証明|示しなさい|示せ")),
    ("翻訳・読解", re.compile(r"和訳|英訳|訳し|本文|読み取")),
)


def analyze_past_questions(questions):
    unique_questions = {}
    for question in questions:
        key = normalize_answer(question.get("question", ""))
        if key:
            unique_questions.setdefault(key, question)

    topic_labels = {}
    topic_counts = Counter()
    format_counts = Counter()
    for question in unique_questions.values():
        topic = question.get("topic", "").strip()
        if topic:
            topic_key = normalize_answer(topic)
            topic_labels.setdefault(topic_key, topic)
            topic_counts[topic_key] += 1
        text = question.get("question", "")
        for label, pattern in QUESTION_FORMATS:
            if pattern.search(text):
                format_counts[label] += 1

    return {
        "question_count": len(unique_questions),
        "topic_counts": [
            (topic_labels[key], count)
            for key, count in topic_counts.most_common()
        ],
        "format_counts": format_counts.most_common(),
    }


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


def load_past_questions():
    try:
        data = json.loads(PAST_QUESTIONS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], ""
    except (OSError, json.JSONDecodeError):
        return [], "過去問データを読み込めません。"
    if not isinstance(data, list):
        return [], "過去問データの形式が正しくありません。"
    questions = []
    for item in data:
        if (
            isinstance(item, dict)
            and all(isinstance(item.get(key), str) for key in ("question", "answer", "solution", "topic"))
        ):
            questions.append(item)
    return questions, ""


def load_progress():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set(), 0, set(), ""
    except (OSError, json.JSONDecodeError):
        return set(), 0, set(), "保存した進捗を読み込めませんでした。学習済み情報はこの起動中のみ保持されます。"
    if not isinstance(data, dict) or not isinstance(data.get("completed"), list):
        return set(), 0, set(), "保存データの形式が正しくありません。学習済み情報はこの起動中のみ保持されます。"
    lesson_ids = {lesson["id"] for lesson in LESSONS}
    completed = {
        item for item in data["completed"] if isinstance(item, str) and item in lesson_ids
    }
    saved_points = data.get("points")
    if saved_points is None:
        points = len(completed) * 10
        awarded_lessons = set(completed)
    elif type(saved_points) is int and saved_points >= 0:
        points = saved_points
        raw_awarded_lessons = data.get("awarded_lessons", list(completed))
        if not isinstance(raw_awarded_lessons, list):
            return (
                completed,
                0,
                set(completed),
                "保存したポイント履歴の形式が正しくありません。今回のポイントは0から開始します。",
            )
        awarded_lessons = {
            item
            for item in raw_awarded_lessons
            if isinstance(item, str) and item in lesson_ids
        }
    else:
        return (
            completed,
            0,
            set(completed),
            "保存ポイントの形式が正しくありません。今回のポイントは0から開始します。",
        )
    return completed, points, awarded_lessons, ""


def main(page: ft.Page):
    page.title = "テスト攻略ラボ | 勉強のコツを学ぼう"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = PAPER
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    completed_lessons, total_points, awarded_lessons, storage_message = load_progress()
    weak_problems, weak_storage_message = load_weak_problems()
    past_questions, past_questions_message = load_past_questions()
    selected_lesson_id = LESSONS[0]["id"]
    selected_grade = "1"
    selected_subject = "数学"
    selected_range_key = "__all__"
    range_topic_options = {}
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
    points_text = ft.Text(size=13, color=GREEN, weight=ft.FontWeight.BOLD)
    points_feedback = ft.Text(size=11, color=GREEN)
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
    topic_text_input = ft.TextField(
        label="教科・範囲",
        hint_text="上で選んだ範囲を問題に登録します",
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
        visible=False,
    )
    grade_selector = ft.Dropdown(
        label="学年",
        value=selected_grade,
        options=[
            ft.DropdownOption(key=grade, text=f"高校{grade}年")
            for grade in HIGH_SCHOOL_CURRICULUM
        ],
        width=180,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
        on_select=lambda event: select_grade(event.control.value),
    )
    subject_selector = ft.Dropdown(
        label="勉強する教科",
        value=selected_subject,
        options=[
            *[
                ft.DropdownOption(key=subject, text=subject)
                for subject in HIGH_SCHOOL_CURRICULUM[selected_grade]
            ],
            ft.DropdownOption(key="すべて", text="すべての教科"),
            ft.DropdownOption(key="その他", text="その他"),
        ],
        width=260,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
        on_select=lambda event: select_subject(event.control.value),
    )
    range_selector = ft.Dropdown(
        label="出題する範囲",
        value=selected_range_key,
        options=[ft.DropdownOption(key="__all__", text="教科全体")],
        width=320,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
        on_select=lambda event: select_range(event.control.value),
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
    prediction_list = ft.Column(spacing=10)
    learned_pattern_panel = ft.Column(spacing=8)
    predicted_test_panel = ft.Column(spacing=12)
    prediction_status = ft.Text(
        past_questions_message,
        size=12,
        color=CORAL if past_questions_message else MUTED,
    )
    active_problem = None
    answer_revealed = False
    answer_checked = False
    photo_points_awarded = False
    predicted_test_questions = []
    predicted_test_index = 0
    predicted_test_score = 0
    predicted_test_answered = False
    predicted_test_answer_revealed = False
    predicted_test_title = "テスト"
    predicted_test_answer_input = ft.TextField(
        label="あなたの解答",
        multiline=True,
        min_lines=1,
        max_lines=3,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor=WHITE,
    )
    predicted_test_feedback = ft.Text(size=12)

    async def choose_photo(event):
        nonlocal active_problem, answer_revealed, answer_checked, photo_points_awarded
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
        photo_points_awarded = False
        photo_problem.controls = []
        photo_preview.visible = False
        question_text_input.visible = False
        topic_text_input.visible = False
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
        topic_text_input.value = ""
        topic_text_input.visible = True
        answer_text_input.value = ""
        answer_text_input.visible = True
        solution_text_input.value = ""
        solution_text_input.visible = True
        make_photo_problem_button.visible = True
        photo_status.value = "読み取りました。問題文を確認・修正してから出題してください。"
        photo_status.color = GREEN
        page.update()

    def show_problem(event):
        nonlocal active_problem, answer_revealed, answer_checked, photo_points_awarded
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
        topic = (topic_text_input.value or "").strip()
        if selected_range_key != "__all__":
            topic = range_topic_options[selected_range_key]
        elif selected_subject != "すべて" and not topic_matches_subject(topic, selected_subject):
            topic = f"{selected_subject}・{topic}" if topic else selected_subject
        active_problem = {
            "question": question,
            "answer": answer,
            "solution": solution,
            "topic": topic,
            "grade": selected_grade,
        }
        question_key = normalize_answer(question)
        existing_index = next(
            (
                index
                for index, item in enumerate(past_questions)
                if normalize_answer(item["question"]) == question_key
            ),
            None,
        )
        previous_question = None
        if existing_index is None:
            past_questions.append(active_problem.copy())
        else:
            previous_question = past_questions[existing_index]
            past_questions[existing_index] = active_problem.copy()
        if save_past_questions():
            prediction_status.value = (
                "同じ問題を更新して保存しました。"
                if previous_question is not None
                else "過去問を保存しました。"
            )
            prediction_status.color = GREEN
        else:
            if existing_index is None:
                past_questions.pop()
            else:
                past_questions[existing_index] = previous_question
            prediction_status.value = "過去問を保存できませんでした。保存先の権限をご確認ください。"
            prediction_status.color = CORAL
        refresh_range_selector()
        render_predictions()
        answer_revealed = False
        answer_checked = False
        photo_points_awarded = False
        photo_answer_input.value = ""
        photo_answer_feedback.value = ""
        photo_answer_feedback.visible = False
        photo_status.value = "問題を出題しました。考えてから答えを確認しましょう。"
        photo_status.color = GREEN
        render_photo_problem()

    def check_photo_answer(event):
        nonlocal answer_revealed, answer_checked, photo_points_awarded
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
            if not photo_points_awarded:
                photo_points_awarded = True
                add_points(5, "写真問題正解 +5 pt")
                persist_progress()
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

    def save_past_questions():
        try:
            PAST_QUESTIONS_FILE.write_text(
                json.dumps(past_questions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return False
        return True

    def questions_for_selected_subject():
        if selected_subject == "すべて":
            return past_questions
        return [
            item
            for item in past_questions
            if topic_matches_subject(item.get("topic", ""), selected_subject)
            and str(item.get("grade", selected_grade)) == selected_grade
        ]

    def refresh_range_selector():
        nonlocal selected_range_key
        topics = {}
        range_topic_options.clear()
        if selected_subject != "すべて":
            for unit in HIGH_SCHOOL_CURRICULUM[selected_grade].get(selected_subject, ()):
                topic = f"{selected_subject}・{unit}"
                topic_key = normalize_answer(topic)
                topics[topic_key] = unit
                range_topic_options[topic_key] = topic
        for item in questions_for_selected_subject():
            topic = item.get("topic", "").strip()
            topic_key = normalize_answer(topic)
            if topic_key:
                topics.setdefault(topic_key, topic)
                range_topic_options.setdefault(topic_key, topic)
        range_selector.options = [
            ft.DropdownOption(key="__all__", text="教科全体"),
            *[
                ft.DropdownOption(
                    key=topic_key,
                    text=topic if selected_subject == "すべて" else topic_scope_label(
                        range_topic_options[topic_key], selected_subject
                    ),
                )
                for topic_key, topic in sorted(topics.items(), key=lambda entry: entry[1])
            ],
        ]
        if selected_range_key != "__all__" and selected_range_key not in topics:
            selected_range_key = "__all__"
        range_selector.value = selected_range_key

    def select_range(range_key):
        nonlocal selected_range_key
        selected_range_key = range_key or "__all__"
        if selected_range_key == "__all__":
            topic_text_input.hint_text = "選んだ教科の問題を登録できます"
        else:
            topic = range_topic_options[selected_range_key]
            label = topic_scope_label(topic, selected_subject) if selected_subject != "すべて" else topic
            topic_text_input.hint_text = f"登録する問題の範囲：「{label}」"
        page.update()

    def learn_past_questions(event):
        analysis = analyze_past_questions(questions_for_selected_subject())
        learned_pattern_panel.controls = [
            ft.Text(
                f"学習した過去問：{analysis['question_count']}問",
                size=13,
                color=INK,
                weight=ft.FontWeight.W_600,
            )
        ]
        if analysis["question_count"] == 0:
            learned_pattern_panel.controls.append(
                ft.Text("まず過去問を撮影して、模範解答と教科・単元を登録してください。", size=12, color=MUTED)
            )
        else:
            repeated_topics = [
                (topic, count)
                for topic, count in analysis["topic_counts"]
                if count >= 2
            ]
            learned_pattern_panel.controls.append(
                ft.Text("頻出テーマ", size=12, color=GREEN, weight=ft.FontWeight.BOLD)
            )
            if repeated_topics:
                for topic, count in repeated_topics[:5]:
                    learned_pattern_panel.controls.append(
                        ft.Text(f"・{topic}：{count}問", size=12, color=INK)
                    )
            else:
                learned_pattern_panel.controls.append(
                    ft.Text("同じ教科・単元の過去問はまだ複数ありません。", size=12, color=MUTED)
                )

            repeated_formats = [
                (question_format, count)
                for question_format, count in analysis["format_counts"]
                if count >= 2
            ]
            learned_pattern_panel.controls.append(
                ft.Text("繰り返し見られる出題形式", size=12, color=GREEN, weight=ft.FontWeight.BOLD)
            )
            if repeated_formats:
                for question_format, count in repeated_formats:
                    learned_pattern_panel.controls.append(
                        ft.Text(f"・{question_format}：{count}問", size=12, color=INK)
                    )
            else:
                learned_pattern_panel.controls.append(
                    ft.Text("同じ出題形式の繰り返しはまだ見つかりません。", size=12, color=MUTED)
                )
            learned_pattern_panel.controls.append(
                ft.Text(
                    "これは保存した問題文の語句と単元の集計です。実際の出題を保証するものではありません。",
                    size=11,
                    color=MUTED,
                )
            )
        page.update()

    def start_predicted_test(topic_key):
        questions = [
            item.copy()
            for item in questions_for_selected_subject()
            if normalize_answer(item.get("topic", "")) == topic_key
        ]
        begin_test(questions, "予想テスト")

    def start_range_test(event):
        questions = questions_for_selected_subject()
        if selected_range_key != "__all__":
            questions = [
                item for item in questions
                if normalize_answer(item.get("topic", "")) == selected_range_key
            ]
        if not questions:
            predicted_test_panel.controls = [
                ft.Text("この範囲の問題はまだありません。過去問を登録してください。", size=13, color=MUTED)
            ]
            page.update()
            return
        subject_label = "すべての教科" if selected_subject == "すべて" else selected_subject
        if selected_subject != "すべて":
            subject_label = f"高校{selected_grade}年・{subject_label}"
        range_label = "教科全体"
        if selected_range_key != "__all__":
            topic = next(
                item.get("topic", "")
                for item in questions
                if normalize_answer(item.get("topic", "")) == selected_range_key
            )
            range_label = topic_scope_label(topic, selected_subject)
        begin_test(questions, f"{subject_label}・{range_label}")

    def begin_test(questions, title):
        nonlocal predicted_test_questions, predicted_test_index
        nonlocal predicted_test_score, predicted_test_answered, predicted_test_answer_revealed
        nonlocal predicted_test_title
        predicted_test_questions = [item.copy() for item in questions]
        predicted_test_index = 0
        predicted_test_score = 0
        predicted_test_answered = False
        predicted_test_answer_revealed = False
        predicted_test_title = title
        predicted_test_answer_input.value = ""
        predicted_test_feedback.value = ""
        render_predicted_test()

    def reveal_predicted_test_answer(event):
        nonlocal predicted_test_answer_revealed
        if predicted_test_answered or not predicted_test_questions:
            return
        predicted_test_answer_revealed = True
        render_predicted_test()

    def answer_predicted_test(event):
        nonlocal predicted_test_score, predicted_test_answered
        if predicted_test_answered or not predicted_test_questions:
            return
        user_answer = (predicted_test_answer_input.value or "").strip()
        if not user_answer:
            predicted_test_feedback.value = "解答を入力してから答え合わせしてください。"
            predicted_test_feedback.color = CORAL
            page.update()
            return

        problem = predicted_test_questions[predicted_test_index]
        predicted_test_answered = True
        if normalize_answer(user_answer) == normalize_answer(problem["answer"]):
            predicted_test_score += 1
            predicted_test_feedback.value = "正解！ 5ポイント獲得。"
            predicted_test_feedback.color = GREEN
            add_points(5, "予想テスト正解 +5 pt")
            persist_progress()
        else:
            predicted_test_feedback.value = f"不正解。模範解答：{problem['answer']}"
            predicted_test_feedback.color = CORAL
            record_weak_problem(problem)
        render_predicted_test()

    def advance_predicted_test(event):
        nonlocal predicted_test_index, predicted_test_answered, predicted_test_answer_revealed
        predicted_test_index += 1
        predicted_test_answered = False
        predicted_test_answer_revealed = False
        predicted_test_answer_input.value = ""
        predicted_test_feedback.value = ""
        render_predicted_test()

    def render_predicted_test():
        predicted_test_panel.controls = []
        if not predicted_test_questions:
            page.update()
            return
        if predicted_test_index >= len(predicted_test_questions):
            predicted_test_panel.controls = [
                ft.Text("テスト終了！", size=16, color=INK, weight=ft.FontWeight.W_600),
                ft.Text(
                    f"{predicted_test_title}：{len(predicted_test_questions)}問中 {predicted_test_score}問正解",
                    size=14,
                    color=GREEN,
                ),
                ft.Button(
                    "もう一度解く",
                    on_click=lambda event: begin_test(predicted_test_questions, predicted_test_title),
                    bgcolor=GREEN,
                    color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                ),
            ]
            page.update()
            return

        problem = predicted_test_questions[predicted_test_index]
        predicted_test_panel.controls = [
            ft.Text(
                f"{predicted_test_title}  {predicted_test_index + 1} / {len(predicted_test_questions)}",
                size=12,
                color=GREEN,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(problem["question"], size=16, color=INK, weight=ft.FontWeight.W_600),
            predicted_test_answer_input,
        ]
        if predicted_test_answered:
            predicted_test_panel.controls.extend(
                [
                    ft.Container(
                        content=ft.Text(predicted_test_feedback.value, size=12, color=predicted_test_feedback.color),
                        padding=12,
                        bgcolor=GREEN_LIGHT if predicted_test_feedback.color == GREEN else "#F9E9E4",
                        border_radius=6,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("解き方", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                                ft.Text(problem["solution"], size=13, color=INK),
                            ],
                            spacing=6,
                        ),
                        padding=12,
                        bgcolor=GREEN_LIGHT,
                        border_radius=6,
                    ),
                    ft.Button(
                        "次の問題" if predicted_test_index < len(predicted_test_questions) - 1 else "結果を見る",
                        on_click=advance_predicted_test,
                        bgcolor=GREEN,
                        color="white",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                    ),
                ]
            )
        elif predicted_test_answer_revealed:
            predicted_test_panel.controls.extend(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("模範解答", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                                ft.Text(problem["answer"], size=14, color=INK),
                                ft.Text("解き方", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                                ft.Text(problem["solution"], size=13, color=INK),
                            ],
                            spacing=6,
                        ),
                        padding=12,
                        bgcolor=GREEN_LIGHT,
                        border_radius=6,
                    ),
                    ft.Text("答えを確認したため、この問題は採点されません。", size=11, color=MUTED),
                    ft.Button(
                        "次の問題" if predicted_test_index < len(predicted_test_questions) - 1 else "結果を見る",
                        on_click=advance_predicted_test,
                        bgcolor=GREEN,
                        color="white",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                    ),
                ]
            )
        else:
            predicted_test_panel.controls.append(
                ft.Button(
                    "答え合わせ",
                    on_click=answer_predicted_test,
                    bgcolor=GREEN,
                    color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                )
            )
            predicted_test_panel.controls.append(
                ft.Button(
                    "答えを見る（詰まったとき）",
                    on_click=reveal_predicted_test_answer,
                    bgcolor=GREEN_LIGHT,
                    color=GREEN,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                )
            )
        page.update()

    def render_predictions():
        analysis = analyze_past_questions(questions_for_selected_subject())
        topic_labels = {
            normalize_answer(topic): topic
            for topic, _ in analysis["topic_counts"]
        }
        recurring_topics = [
            (topic_labels[normalize_answer(topic)], count, normalize_answer(topic))
            for topic, count in analysis["topic_counts"]
            if count >= 2
        ][:3]
        prediction_list.controls = []
        if analysis["question_count"] < 2:
            subject_label = "この教科の過去問" if selected_subject != "すべて" else "過去問"
            question_count_message = (
                f"{subject_label}を2問登録すると、傾向を表示します。"
                if analysis["question_count"] == 0
                else f"{subject_label}をあと1問登録すると、傾向を表示します。"
            )
            prediction_list.controls.append(
                ft.Text(question_count_message, size=13, color=MUTED)
            )
        elif not recurring_topics:
            prediction_list.controls.append(
                ft.Text(
                    f"過去問を{analysis['question_count']}問保存しました。教科・単元を同じ名前で複数登録すると、頻出テーマを予測できます。",
                    size=13,
                    color=MUTED,
                )
            )
        else:
            prediction_list.controls.append(
                ft.Text(
                    "保存した過去問のテーマ出現回数から、復習候補を表示しています。出題を保証するものではありません。",
                    size=12,
                    color=MUTED,
                )
            )
            for topic, count, topic_key in recurring_topics:
                example = next(
                    item
                    for item in questions_for_selected_subject()
                    if normalize_answer(item["topic"]) == topic_key
                )
                prediction_list.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(topic, size=15, color=INK, weight=ft.FontWeight.W_600),
                                        ft.Text(f"過去問に {count} 回", size=11, color=CORAL),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(
                                    f"出題予想：この単元の類題や応用問題を優先して復習しましょう。",
                                    size=12,
                                    color=GREEN,
                                ),
                                ft.Text(f"参考にする過去問：{example['question']}", size=12, color=MUTED),
                                ft.Button(
                                    f"「{topic}」の予想テストに挑戦",
                                    on_click=lambda event, key=topic_key: start_predicted_test(key),
                                    bgcolor=GREEN,
                                    color="white",
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                                ),
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

    def select_subject(subject):
        nonlocal selected_subject, selected_range_key, predicted_test_questions
        selected_subject = subject or "すべて"
        selected_range_key = "__all__"
        range_selector.value = selected_range_key
        refresh_range_selector()
        topic_text_input.label = (
            f"単元（高校{selected_grade}年・{selected_subject}）"
            if selected_subject != "すべて"
            else "教科・単元"
        )
        topic_text_input.hint_text = (
            f"高校{selected_grade}年・{selected_subject}の範囲に登録します"
            if selected_subject != "すべて"
            else "教科全体から出題します"
        )
        predicted_test_questions = []
        render_predicted_test()
        render_predictions()
        if learned_pattern_panel.controls:
            learn_past_questions(None)

    def select_grade(grade):
        nonlocal selected_grade, selected_subject
        selected_grade = grade if grade in HIGH_SCHOOL_CURRICULUM else "1"
        grade_selector.value = selected_grade
        subjects = HIGH_SCHOOL_CURRICULUM[selected_grade]
        subject_selector.options = [
            *[
                ft.DropdownOption(key=subject, text=subject)
                for subject in subjects
            ],
            ft.DropdownOption(key="すべて", text="すべての教科"),
            ft.DropdownOption(key="その他", text="その他"),
        ]
        if selected_subject not in subjects and selected_subject not in ("すべて", "その他"):
            selected_subject = next(iter(subjects))
        subject_selector.value = selected_subject
        select_subject(selected_subject)

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
    learn_past_questions_button = ft.Button(
        "保存した過去問を学習する",
        on_click=learn_past_questions,
        bgcolor=GREEN,
        color="white",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
    )
    start_range_test_button = ft.Button(
        "この範囲の問題を出す",
        on_click=start_range_test,
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
                json.dumps(
                    {
                        "completed": sorted(completed_lessons),
                        "points": total_points,
                        "awarded_lessons": sorted(awarded_lessons),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            storage_message = ""
        except OSError:
            storage_message = "進捗を保存できませんでした。書き込み権限をご確認ください。"
        notice.value = storage_message
        notice.visible = bool(storage_message)

    def add_points(amount, reason):
        nonlocal total_points
        total_points += amount
        points_text.value = f"★ {total_points} ポイント"
        points_feedback.value = f"{reason}を獲得！"

    def render_progress():
        count = len(completed_lessons)
        total = len(LESSONS)
        progress_text.value = f"{count} / {total} レッスン完了"
        points_text.value = f"★ {total_points} ポイント"
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
            if lesson_id not in awarded_lessons:
                awarded_lessons.add(lesson_id)
                add_points(10, "レッスン完了 +10 pt")
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
            add_points(5, "クイズ正解 +5 pt")
            persist_progress()
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
    lesson_layout = ft.Column(
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
                                ft.Row([progress_text, points_text], spacing=12),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        points_feedback,
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
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [grade_selector, subject_selector],
                            wrap=True,
                            spacing=10,
                            run_spacing=8,
                        ),
                        ft.Text(
                            "高校の学年に合わせた教科・範囲から選び、登録済みの問題を出題します。",
                            size=12,
                            color=MUTED,
                        ),
                        ft.Row(
                            [range_selector, start_range_test_button],
                            wrap=True,
                            spacing=10,
                            run_spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            "選んだ学年・教科・範囲は、過去問の分析と問題登録にも反映されます。",
                            size=11,
                            color=MUTED,
                        ),
                        predicted_test_panel,
                    ],
                    spacing=8,
                ),
                padding=16,
                bgcolor=WHITE,
                border=ft.Border.all(1, "#E3E3D9"),
                border_radius=8,
            ),
            ft.Text("攻略レッスン", size=20, color=INK, weight=ft.FontWeight.W_600),
            lesson_layout,
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
                        topic_text_input,
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
            ft.Text("過去問から出題を予測", size=20, color=INK, weight=ft.FontWeight.W_600),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "保存した過去問で同じ教科・単元が繰り返し出ているかを見て、復習候補を表示します。未来の出題を保証するものではありません。",
                            size=12,
                            color=MUTED,
                        ),
                        learn_past_questions_button,
                        learned_pattern_panel,
                        prediction_status,
                        prediction_list,
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
        lesson_layout.controls[0].width = min(300, content_width)
        page.update()

    page.on_resize = resize_page
    page.add(app_container)
    render_progress()
    render_lessons()
    refresh_range_selector()
    render_predictions()
    render_weak_problems()
    render_quiz()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
