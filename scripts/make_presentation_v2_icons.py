import os
from datetime import datetime

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE

# --- Theme ---
NAVY = RGBColor(0x0B, 0x2A, 0x4A)
RED = RGBColor(0xD9, 0x2D, 0x2A)
LIGHT_BG = RGBColor(0xF6, 0xF8, 0xFB)
TEXT = RGBColor(0x10, 0x18, 0x28)
MUTED = RGBColor(0x47, 0x56, 0x67)
BORDER = RGBColor(0xD0, 0xD5, 0xDD)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

TITLE_FONT = "Segoe UI"
BODY_FONT = "Segoe UI"


def _set_run(run, *, size=None, bold=None, color=None, font=None):
    f = run.font
    if font:
        f.name = font
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if color:
        f.color.rgb = color


def add_top_bar(slide, title_left="СухоVL", right_text=""):
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.62)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.12), Inches(7), Inches(0.4))
    tf = tb.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title_left
    _set_run(run, size=18, bold=True, color=WHITE, font=TITLE_FONT)

    if right_text:
        rb = slide.shapes.add_textbox(Inches(9.2), Inches(0.14), Inches(3.9), Inches(0.35))
        rtf = rb.text_frame
        rtf.clear()
        rp = rtf.paragraphs[0]
        rp.alignment = PP_ALIGN.RIGHT
        rrun = rp.add_run()
        rrun.text = right_text
        _set_run(rrun, size=13, bold=False, color=WHITE, font=TITLE_FONT)


def add_title(slide, title, subtitle=None):
    box = slide.shapes.add_textbox(Inches(0.85), Inches(0.95), Inches(11.8), Inches(0.9))
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    _set_run(run, size=34, bold=True, color=TEXT, font=TITLE_FONT)

    if subtitle:
        sb = slide.shapes.add_textbox(Inches(0.85), Inches(1.78), Inches(11.5), Inches(0.55))
        stf = sb.text_frame
        stf.clear()
        sp = stf.paragraphs[0]
        srun = sp.add_run()
        srun.text = subtitle
        _set_run(srun, size=16, bold=False, color=MUTED, font=BODY_FONT)


def add_section_badge(slide, text):
    badge = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.85), Inches(2.55), Inches(3.2), Inches(0.45)
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = RED
    badge.line.fill.background()
    tf = badge.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    _set_run(run, size=13, bold=True, color=WHITE, font=BODY_FONT)


def add_bullets(slide, bullets, *, x=0.95, y=2.25, w=6.35, h=4.8, font_size=20):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.clear()

    for i, b in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = b
        p.level = 0
        p.space_after = Pt(6)
        for run in p.runs:
            _set_run(run, size=font_size, color=TEXT, font=BODY_FONT)


def add_note(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def add_placeholder(slide, label, *, x, y, w, h):
    rect = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    rect.fill.solid()
    rect.fill.fore_color.rgb = LIGHT_BG
    rect.line.color.rgb = BORDER
    rect.line.width = Pt(1.5)

    tf = rect.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = label
    _set_run(run, size=16, bold=True, color=MUTED, font=BODY_FONT)


def add_small_caption(slide, text, *, x, y, w=5.5):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.3))
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    _set_run(run, size=12, color=MUTED, font=BODY_FONT)


def add_icon(slide, kind: str, *, x, y, size=0.75):
    # simple line icons made from basic shapes (no external images)
    s = Inches(size)

    def stroke(shape, color=NAVY, width=2.25):
        shape.fill.background()
        shape.line.color.rgb = color
        shape.line.width = Pt(width)

    if kind == "rain":
        cloud = slide.shapes.add_shape(MSO_SHAPE.CLOUD, Inches(x), Inches(y), s*1.25, s*0.9)
        stroke(cloud, NAVY)
        # raindrops (simple ovals)
        for i in range(3):
            d = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x)+Inches(0.14+i*0.28), Inches(y)+Inches(0.58), Inches(0.14), Inches(0.22))
            d.fill.solid(); d.fill.fore_color.rgb = RED
            d.line.fill.background()
    elif kind == "map_pin":
        # Pin made from circle + triangle (TEARDROP not available in some pptx builds)
        circ = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x)+Inches(0.22), Inches(y), Inches(0.32), Inches(0.32))
        circ.fill.background(); circ.line.color.rgb = RED; circ.line.width = Pt(2.25)
        tri = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, Inches(x)+Inches(0.27), Inches(y)+Inches(0.22), Inches(0.22), Inches(0.34))
        tri.fill.background(); tri.line.color.rgb = RED; tri.line.width = Pt(2.25)
        tri.rotation = 180
        c = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x)+Inches(0.32), Inches(y)+Inches(0.10), Inches(0.12), Inches(0.12))
        c.fill.solid(); c.fill.fore_color.rgb = NAVY
        c.line.fill.background()
    elif kind == "car":
        body = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y)+Inches(0.2), s*1.25, s*0.55)
        stroke(body, NAVY)
        w1 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x)+Inches(0.18), Inches(y)+Inches(0.62), Inches(0.22), Inches(0.22))
        w2 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x)+Inches(0.80), Inches(y)+Inches(0.62), Inches(0.22), Inches(0.22))
        stroke(w1, RED)
        stroke(w2, RED)
    elif kind == "shield":
        # Approximate shield with a rounded rectangle (SHIELD not available everywhere)
        sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x)+Inches(0.05), Inches(y), s*1.0, s*1.05)
        stroke(sh, NAVY)
        # check mark
        l1 = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(x)+Inches(0.35), Inches(y)+Inches(0.62), Inches(0.18), Inches(0.18))
        l1.line.color.rgb = RED
        l1.line.width = Pt(3)
        l2 = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(x)+Inches(0.48), Inches(y)+Inches(0.75), Inches(0.32), Inches(-0.32))
        l2.line.color.rgb = RED
        l2.line.width = Pt(3)
    elif kind == "gear":
        g = slide.shapes.add_shape(MSO_SHAPE.GEAR_6, Inches(x), Inches(y), s, s)
        stroke(g, NAVY)
        hole = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x)+Inches(0.22), Inches(y)+Inches(0.22), Inches(0.31), Inches(0.31))
        stroke(hole, RED)
    elif kind == "ai":
        # chat bubble + spark
        bub = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y)+Inches(0.1), s*1.2, s*0.7)
        stroke(bub, NAVY)
        spark = slide.shapes.add_shape(MSO_SHAPE.STAR_4_POINT, Inches(x)+Inches(0.85), Inches(y), Inches(0.35), Inches(0.35))
        stroke(spark, RED)
    elif kind == "timeline":
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y)+Inches(0.35), s*1.35, Inches(0.06))
        line.fill.solid(); line.fill.fore_color.rgb = NAVY
        line.line.fill.background()
        for i, col in enumerate([RED, NAVY, RED]):
            dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x)+Inches(0.05+i*0.45), Inches(y)+Inches(0.25), Inches(0.18), Inches(0.18))
            dot.fill.solid(); dot.fill.fore_color.rgb = col
            dot.line.fill.background()
    elif kind == "next":
        arr = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y)+Inches(0.18), s*1.2, s*0.6)
        arr.fill.solid(); arr.fill.fore_color.rgb = RED
        arr.line.fill.background()
        chk = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x)+Inches(0.9), Inches(y), Inches(0.32), Inches(0.32))
        chk.fill.background(); chk.line.color.rgb = NAVY; chk.line.width = Pt(2)
        mark = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(x)+Inches(0.98), Inches(y)+Inches(0.18), Inches(0.08), Inches(0.08))
        mark.line.color.rgb = RED; mark.line.width = Pt(2.5)
        mark2 = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(x)+Inches(1.04), Inches(y)+Inches(0.24), Inches(0.16), Inches(-0.16))
        mark2.line.color.rgb = RED; mark2.line.width = Pt(2.5)
    else:
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(0.2), Inches(0.2))
        dot.fill.solid(); dot.fill.fore_color.rgb = RED
        dot.line.fill.background()


def slide_layout_blank(prs):
    return prs.slide_layouts[6]


def add_content_slide(prs, title, bullets, *, right_placeholders=None, note=None, right_title=None, icon=None):
    slide = prs.slides.add_slide(slide_layout_blank(prs))
    add_top_bar(slide)

    tbox = slide.shapes.add_textbox(Inches(0.85), Inches(0.9), Inches(12.0), Inches(0.7))
    tf = tbox.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    _set_run(run, size=28, bold=True, color=TEXT, font=TITLE_FONT)

    if icon:
        add_icon(slide, icon, x=12.2, y=0.82, size=0.55)

    add_bullets(slide, bullets, x=0.95, y=1.8, w=7.0, h=5.2, font_size=18)

    if right_placeholders:
        if right_title:
            add_small_caption(slide, right_title, x=8.25, y=1.55, w=4.9)
        y = 1.85
        for ph in right_placeholders:
            add_placeholder(slide, ph, x=8.2, y=y, w=4.7, h=1.35)
            y += 1.55
        add_small_caption(slide, "Скриншоты будут добавлены пользователем позже", x=8.2, y=6.55, w=4.8)

    if note:
        add_note(slide, note)

    return slide


def add_title_slide(prs):
    slide = prs.slides.add_slide(slide_layout_blank(prs))
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid(); bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()

    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(6.85), Inches(13.333), Inches(0.65))
    stripe.fill.solid(); stripe.fill.fore_color.rgb = RED
    stripe.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(0.9), Inches(2.2), Inches(12.0), Inches(1.2))
    tf = tb.text_frame; tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run(); run.text = "СухоVL"
    _set_run(run, size=56, bold=True, color=WHITE, font=TITLE_FONT)

    sb = slide.shapes.add_textbox(Inches(0.92), Inches(3.35), Inches(12.0), Inches(0.6))
    stf = sb.text_frame; stf.clear()
    sp = stf.paragraphs[0]
    srun = sp.add_run(); srun.text = "Народная карта подтоплений Владивостока"
    _set_run(srun, size=20, bold=False, color=WHITE, font=BODY_FONT)

    # small stickman doodle (vector)
    # head
    head = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(10.9), Inches(2.35), Inches(0.45), Inches(0.45))
    head.fill.background(); head.line.color.rgb = WHITE; head.line.width = Pt(2)
    # body line
    body = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(11.12), Inches(2.8), Inches(0), Inches(0.8))
    body.line.color.rgb = WHITE; body.line.width = Pt(2)
    # arms
    arm1 = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(11.12), Inches(3.05), Inches(-0.35), Inches(0.2))
    arm2 = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(11.12), Inches(3.05), Inches(0.35), Inches(0.2))
    for a in (arm1, arm2):
        a.line.color.rgb = WHITE; a.line.width = Pt(2)
    # legs
    leg1 = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(11.12), Inches(3.6), Inches(-0.3), Inches(0.5))
    leg2 = slide.shapes.add_shape(MSO_SHAPE.LINE_INVERSE, Inches(11.12), Inches(3.6), Inches(0.3), Inches(0.5))
    for l in (leg1, leg2):
        l.line.color.rgb = WHITE; l.line.width = Pt(2)
    # umbrella
    umb = slide.shapes.add_shape(MSO_SHAPE.ARC, Inches(10.45), Inches(2.55), Inches(0.9), Inches(0.6))
    umb.line.color.rgb = RED; umb.line.width = Pt(2)

    fb = slide.shapes.add_textbox(Inches(0.95), Inches(6.98), Inches(12.0), Inches(0.4))
    ftf = fb.text_frame; ftf.clear()
    fp = ftf.paragraphs[0]
    fr = fp.add_run(); fr.text = "Хакатон · 3–5 минутный питч"
    _set_run(fr, size=14, color=WHITE, font=BODY_FONT)

    add_note(slide, "Коротко: что такое СухоVL и зачем он нужен городу. 10–15 секунд.")
    return slide


def build(prs: Presentation):
    add_title_slide(prs)

    add_content_slide(prs, "Проблема", [
        "После ливня информация о затоплениях разрознена (чаты/соцсети)",
        "Сложно понять, где реально опасно прямо сейчас",
        "Нужна оперативная карта и общественная верификация",
        "Нужна модерация, чтобы отсекать мусорные фото/комменты",
    ], note="Сформулировать боль: скорость, достоверность и удобство в одном месте.", icon="rain")

    add_content_slide(prs, "Решение: как работает СухоVL", [
        "Открываю карту → сообщаю о происшествии",
        "Уточняю точку на карте и адрес",
        "Добавляю фото и комментарий (необязательно)",
        "Отправляю: метка уходит на проверку",
        "После одобрения появляется на карте для всех",
    ], right_placeholders=["Экран 1: выбор фото (камера/галерея)", "Экран 2: карта + «Сообщить…»"],
       right_title="Плейсхолдеры под скриншоты",
       note="Коротко проговорить путь пользователя: 2–3 тапа, без регистрации.", icon="map_pin")

    add_content_slide(prs, "Кейсы применения (после ливня/тайфуна)", [
        "Оперативная карта затоплений «здесь и сейчас»",
        "Точки не «висят вечно»: есть таймер актуальности",
        "Подтверждения жителей продлевают актуальность",
        "Подходит для быстрых сводок по районам (идея)",
    ], note="Подчеркнуть: это инструмент на первые часы после непогоды.", icon="rain")

    add_content_slide(prs, "Кейсы применения (водители/пешеходы)", [
        "Предупреждения о проблемных местах рядом (идея)",
        "Пешеходам: где не пройти / гололёд / наледь",
        "Водителям: лужи/подтопления/провалы как риск",
        "Шаринг ссылки на конкретную точку (идея)",
    ], note="Не обещать, помечать идеи как идеи.", icon="car")

    add_content_slide(prs, "Кейсы применения (городские службы)", [
        "Карта как «очередь инцидентов» по улицам",
        "Подтверждения/опровержения = приоритезация",
        "Можно фильтровать по серьёзности (low/medium/high)",
        "Экспорт в CSV/GeoJSON для служб (план/идея)",
    ], note="Смысл: помочь с приоритизацией и маршрутизацией.", icon="shield")

    add_content_slide(prs, "Кейсы применения (общественная верификация)", [
        "Голосование по каждой точке: confirm / deny",
        "Один человек — один голос (обезличенный ключ)",
        "Можно изменить или отменить голос",
        "Видно: сколько подтвердили / сколько опровергли",
    ], right_placeholders=["Экран 1: попап точки + кнопки confirm/deny"], right_title="Плейсхолдер",
       note="Показать, что доверие строится на голосах и модерации.", icon="shield")

    add_content_slide(prs, "Мобильная версия (плейсхолдеры)", [
        "Адаптивный интерфейс: карта + кнопка «Сообщить о происшествии»",
        "Попап точки: фото, статусы, подтверждения/опровержения",
        "Добавление фото: bottom-sheet «Камера / Галерея»",
        "Скриншоты будут добавлены пользователем позже",
    ], right_placeholders=["Экран 1: мобильная карта + FAB", "Экран 2: попап точки", "Экран 3: bottom-sheet фото"],
       right_title="Плейсхолдеры под скриншоты", note="Слайд-папка под мобильные скрины.", icon="map_pin")

    add_content_slide(prs, "Настольная версия (плейсхолдеры)", [
        "Всё на карте: точки, попапы, голосование",
        "Подходит для диспетчера/оператора/сводки",
        "Скриншоты будут добавлены пользователем позже",
    ], right_placeholders=["Экран 1: десктопная карта + попап"], right_title="Плейсхолдер",
       note="Слайд-папка под десктопный скрин.", icon="map_pin")

    add_content_slide(prs, "Модерация и качество данных", [
        "Фото и комментарии проходят проверку",
        "Спорное — решает админ вручную",
        "Фото «главнее»: если фото отклонено — точка скрывается целиком",
        "Публикация только после одобрения",
    ], note="Важно: карта не превращается в помойку — есть фильтрация и ручной контроль.", icon="shield")

    add_content_slide(prs, "Кабинет разработчика: вход (/login)", [
        "Один аккаунт из .env (DEV_LOGIN / DEV_PASSWORD)",
        "Регистрации нет",
        "Нужен для модерации и настройки ИИ",
    ], right_placeholders=["Экран 1: /login (логин/пароль/кнопка)"], right_title="Плейсхолдер",
       note="Сказать, что доступ управляется через .env и перезапуск.", icon="gear")

    add_content_slide(prs, "Кабинет: настройки ИИ", [
        "Провайдер: OpenAI-совместимый сервис (gptunnel) или GigaChat",
        "Endpoint / model / timeout / max_tokens — редактируются",
        "Ключи — как секреты (в UI не светим)",
    ], right_placeholders=["Экран 1: «Модель и проверка» (provider/endpoint/model/тайминги)"],
       right_title="Плейсхолдер", note="Показать вкладку настроек модели.", icon="ai")

    add_content_slide(prs, "Кабинет: режим модерации", [
        "Режимы: ai / manual / off",
        "ai: ИИ проверяет, спорное — вручную",
        "manual: всё решает разработчик",
        "off: проверка отключена (режим тестов)",
    ], note="Важно: можно быстро переключить режим под ситуацию.", icon="shield")

    add_content_slide(prs, "Кабинет: промпты проверки", [
        "Два промпта: отдельно для фото и отдельно для текста",
        "ИИ отвечает строго JSON: verdict + reason",
        "Если ответ «ломается» — метка идёт на ручную модерацию",
    ], right_placeholders=["Экран 1: вкладка «Промпты» + кнопка «Сохранить»"], right_title="Плейсхолдер",
       note="Сказать: промпты можно править без деплоя.", icon="ai")

    add_content_slide(prs, "Кабинет: тексты уведомлений", [
        "Редактируемые тексты интерфейса (загрузка, подсказки, успех/ошибка)",
        "Можно подстроить тон под аудиторию",
        "Ускоряет итерации в бетатестах",
    ], right_placeholders=["Экран 1: вкладка «Тексты уведомлений»"], right_title="Плейсхолдер",
       note="Показать набор полей с текстами.", icon="gear")

    add_content_slide(prs, "Кабинет: очередь модерации", [
        "Фильтры по статусам: pending / rejected / published / all",
        "Карточки с фото и результатом ИИ (verdict/reason)",
        "Ручные кнопки approve/reject",
    ], right_placeholders=["Экран 1: «Очередь модерации»", "Экран 2: карточка с кнопками"],
       right_title="Плейсхолдеры", note="Кнопки доступны и в попапах карты под dev-аккаунтом.", icon="shield")

    add_content_slide(prs, "Алгоритмы и логика (по коду)", [
        "Гео приоритетнее IP: сначала user_lat/user_lng, потом IP-координаты",
        "«Внутри города»: радиус от центра Вл-ка 30 км (GEO_RADIUS_KM), можно отключить GEO_CHECK=0",
        "Голосование: один голос на обезличенный ключ sha256(IP+VOTER_SALT), можно сменить/отменить",
        "Таймер: 12 часов жизни точки; confirm продлевает expires_at и обновляет last_confirmed_at",
        "Модерация: фото главнее; если фото reject — точка скрывается; публикация только после approved",
        "Dev API: анти-CSRF — принимаем только Content-Type: application/json",
    ], note="Быстро, по фактам. Это прям из кода.", icon="ai")

    add_content_slide(prs, "Идеи интеграции с vl.ru (идея)", [
        "Виджет карты на странице новостей про непогоду",
        "Embed iframe / поддомен",
        "Сводка / тепловая карта",
        "Кнопка «Сообщить» из мобильного сайта",
        "Ссылки на конкретные точки (share)",
    ], note="Обязательно проговорить, что это идеи, без обещаний.", icon="map_pin")

    add_content_slide(prs, "Этапы разработки", [
        "Прототип — каркас карты + добавление метки",
        "1-й бетатест — UX на телефоне, подсказки, тексты",
        "2-й бетатест — борьба с мусором, тонкая модерация",
        "Фронтенд — адаптивные панели, попапы, голосование",
        "Финальные правки — безопасность, таймеры, Docker деплой",
    ], note="Держать темп: по 1 фразе на этап.", icon="timeline")

    add_content_slide(prs, "Какие нейросети использовали", [
        "В разработке/ревью/подсказках: Claude Opus 5, Claude Haiku 4.5, Claude Sonnet 4.5, Claude Opus 4.7",
        "Также: GPT‑5.2, DeepSeek v4 Pro, DeepSeek v4.1 Flash",
        "Не отдавали всю работу ИИ: простые правки — вручную",
        "Дорогие модели — для сложных мест, дешёвые — для рутины",
        "Не утверждаем, что именно эти модели стояли в проде",
    ], note="ИИ помогал, но команда контролировала.", icon="ai")

    add_content_slide(prs, "Что не успели (next steps)", [
        "Push-уведомления по району/геозоне",
        "Сводки по районам + простая аналитика",
        "Роли для служб (авторизация/доступы)",
        "Экспорт CSV/GeoJSON",
        "Кластеризация точек",
        "Офлайн-режим/кеш карты",
    ], note="Закрыть питч: что можно сделать дальше.", icon="next")

    slide = prs.slides.add_slide(slide_layout_blank(prs))
    add_top_bar(slide)
    add_title(slide, "Спасибо!", "Вопросы?")
    add_section_badge(slide, "СухоVL")
    add_bullets(slide, [
        "Docker: docker compose up -d --build",
        "Кабинет: /login → /dev",
        "Модерация: AI + ручная очередь",
    ], x=0.95, y=3.2, w=11.5, h=3.0, font_size=20)
    add_note(slide, "Коротко повторить ценность: скорость + карта + верификация. Переход к вопросам.")


def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    build(prs)

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_name = f"Suhovl_pitch_icons_{ts}.pptx"
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    out_path = os.path.join(desktop, out_name)
    prs.save(out_path)
    print(out_path)


if __name__ == "__main__":
    main()
