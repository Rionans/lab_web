from flask import Flask, render_template, request, Response
from flask_wtf import FlaskForm, RecaptchaField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
import os
import net as neuronet
import base64
from PIL import Image
from io import BytesIO
import json
import lxml.etree as ET

import numpy as np
import matplotlib
# чтобы не открывались окна
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wtforms import SelectField, FloatField
from wtforms.validators import NumberRange

app = Flask(__name__)

# Конфигурация приложения
app.config['SECRET_KEY'] = 'secret'
app.config['RECAPTCHA_USE_SSL'] = False
app.config['RECAPTCHA_PUBLIC_KEY'] = '6Lf9mrMsAAAAAARtdfhNhji_KW0Sto0dpCnzYkIs'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6Lf9mrMsAAAAAB_hpIe2ZQHmLdM2J5lM6F2ZUmT8'
app.config['RECAPTCHA_OPTIONS'] = {'theme': 'white'}

bootstrap = Bootstrap(app)

def apply_modulation(img_array, func_type, period):
    h, w = img_array.shape[:2]
    y, x = np.ogrid[:h, :w]
    freq = 2 * np.pi / period
    arg = (x + y) * freq
    pattern = np.sin(arg) if func_type == 'sin' else np.cos(arg)
    pattern_norm = (pattern + 1) / 2.0
    if len(img_array.shape) == 3:
        pattern_norm = pattern_norm[:, :, np.newaxis]
    processed = img_array * pattern_norm
    processed = np.clip(processed * 255, 0, 255).astype(np.uint8)
    return processed

def plot_histogram(img_array, title):
    fig, ax = plt.subplots(figsize=(6, 4))
    if len(img_array.shape) == 3:
        colors = ('red', 'green', 'blue')
        for i, color in enumerate(colors):
            ax.hist(img_array[:, :, i].ravel(), bins=256, range=(0, 1),
                    alpha=0.5, color=color, label=color.upper())
        ax.legend()
    else:
        ax.hist(img_array.ravel(), bins=256, range=(0, 1), color='gray')
    ax.set_xlim(0, 1)
    ax.set_title(title)
    ax.set_xlabel('Интенсивность')
    ax.set_ylabel('Частота')
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

class NetForm(FlaskForm):
    openid = StringField('openid', validators=[DataRequired()])
    upload = FileField(
        'Load image',
        validators=[
            FileRequired(),
            FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
        ]
    )
    # recaptcha = RecaptchaField()
    submit = SubmitField('send')

class ModulationForm(FlaskForm):
    upload = FileField('Load image', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    func = SelectField('Function', choices=[('sin', 'sin'), ('cos', 'cos')],
                       validators=[DataRequired()])
    period = FloatField('Period', validators=[DataRequired(), NumberRange(min=1.0, max=1000.0)],
                        default=50.0)
    recaptcha = RecaptchaField()
    submit = SubmitField('Process')

@app.route("/")
def hello():
    return "<html><head></head><body>Hello World!</body></html>"


@app.route("/data_to")
def data_to():
    some_pars = {'user': 'Ivan', 'color': 'red'}
    some_str = 'Hello my dear friends!'
    some_value = 10
    return render_template(
        'simple.html',
        some_str=some_str,
        some_value=some_value,
        some_pars=some_pars
    )


@app.route("/net", methods=['GET', 'POST'])
def net():
    form = NetForm()
    filename = None
    neurodic = {}

    if form.validate_on_submit():
        filename = os.path.join(
            './static',
            secure_filename(form.upload.data.filename)
        )
        fcount, fimage = neuronet.read_image_files(10, './static')
        decode = neuronet.getresult(fimage)
        for elem in decode:
            neurodic[elem[0][1]] = elem[0][2]
        form.upload.data.save(filename)

    return render_template(
        'net.html',
        form=form,
        image_name=filename,
        neurodic=neurodic
    )

@app.route("/apinet", methods=['GET', 'POST'])
def apinet():
    neurodic = {}
    if request.mimetype == 'application/json':
        data = request.get_json()
        filebytes = data['imagebin'].encode('utf-8')
        cfile = base64.b64decode(filebytes)
        img = Image.open(BytesIO(cfile))
        decode = neuronet.getresult([img])
        neurodic = {}
        for elem in decode:
            neurodic[elem[0][1]] = str(elem[0][2])
        ret = json.dumps(neurodic)
        return Response(response=ret, status=200, mimetype="application/json")
    return Response(response='{}', status=400, mimetype="application/json")

@app.route("/apixml", methods=['GET', 'POST'])
def apixml():
    dom = ET.parse("./static/xml/file.xml")
    xslt = ET.parse("./static/xml/file.xslt")
    transform = ET.XSLT(xslt)
    newhtml = transform(dom)
    strfile = ET.tostring(newhtml)
    return strfile

@app.route("/var19", methods=['GET', 'POST'])
def var19():
    form = ModulationForm()
    original_filename = None
    processed_filename = None
    orig_hist = None
    proc_hist = None

    if form.validate_on_submit():
        # Сохраняем исходный файл
        file = form.upload.data
        ext = os.path.splitext(file.filename)[1]
        original_filename = secure_filename(f"orig_{np.random.randint(10000)}{ext}")
        original_path = os.path.join('./static', original_filename)
        file.save(original_path)

        # Читаем и нормализуем
        img = Image.open(original_path)
        img_array = np.array(img).astype(np.float32) / 255.0

        func_type = form.func.data
        period = form.period.data

        # Обработка
        processed_array = apply_modulation(img_array, func_type, period)
        processed_img = Image.fromarray(processed_array)
        processed_filename = secure_filename(f"proc_{np.random.randint(10000)}{ext}")
        processed_path = os.path.join('./static', processed_filename)
        processed_img.save(processed_path)

        # Гистограммы
        orig_hist = plot_histogram(img_array, "Original Image")
        proc_hist = plot_histogram(processed_array / 255.0, "Processed Image")

    return render_template('var19.html',
                           form=form,
                           original=original_filename,
                           processed=processed_filename,
                           orig_hist=orig_hist,
                           proc_hist=proc_hist)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000)
