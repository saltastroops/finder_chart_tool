from typing import BinaryIO, Dict, Optional

import astropy.units as u
from astropy.units import Quantity
from flask import Flask, render_template, request, send_file
from salt_finder_charts import standard_finder_charts
from salt_finder_charts.mode import Mode
from salt_finder_charts.output import OutputFormat
from salt_finder_charts.image import Survey

app = Flask(__name__)


@app.route('/')
def home():
    return render_template("form.html")


@app.route('/finder_chart', methods=['POST'])
def finder_chart():
    fc = generate_finder_chart(request.form)

    # get MIME type
    output_format: OutputFormat = [of for of in OutputFormat if of.value.lower() == request.form['output_format'].lower()][0]
    mime_type = output_format.mime_type()

    return send_file(fc, mimetype=mime_type, add_etags=False)


def generate_finder_chart(user_input: Dict[str, str]) -> BinaryIO:
    # collect the parameters

    # survey
    if 'survey' not in user_input:
        raise ValueError('survey parameter missing')
    surveys = [s for s in Survey if s.value.lower() == user_input['survey'].lower()]
    if not len(surveys):
        raise ValueError(f"unknown survey: {user_input['survey']}")
    survey = surveys[0]

    # mode
    if 'mode' not in user_input:
        raise ValueError('mode parameter missing')
    modes = [m for m in Mode if m.value.lower() == user_input['mode'].lower()]
    if not len(modes):
        raise ValueError(f"unknown mode: {user_input['mode']}")
    mode = modes[0]

    # output format
    if 'output_format' not in user_input:
        raise ValueError('output_format parameter missing')
    output_formats = [of for of in OutputFormat if of.value.lower() == user_input['output_format'].lower()]
    if not len(output_formats):
        raise ValueError(f"unknown output format: {user_input['output_format']}")
    output_format = output_formats[0]

    # position
    ra = _parse_as_ra(user_input.get('right_ascension', None))
    dec = parse_as_dec(user_input.get('declination', None))

    # MOS Mask
    if 'mos_mask' in request.files and request.files['mos_mask'].filename:
        mos_mask: Optional[BinaryIO] = request.files['mos_mask'].stream
    else:
        mos_mask = None

    # target name
    if 'object_name' not in user_input:
        raise ValueError('object_name parameter missing')
    object_name = user_input['object_name']

    # PI
    if 'pi_name' not in user_input:
        raise ValueError('pi_name parameter missing')
    pi_name = user_input['pi_name']

    # position angle
    if 'position_angle' in user_input:
        pa: Optional[Quantity] = float(user_input['position_angle']) * u.deg
    else:
        pa = None

    # proposal code
    if 'proposal_code'not in user_input:
        raise ValueError('proposal_code parameter missing')
    proposal_code = user_input['proposal_code']

    # magnitude
    bandpass = user_input.get('bandpass', None)
    _min_magnitude = user_input.get('min_magnitude', None)
    _max_magnitude = user_input.get('max_magnitude', None)
    mag_flag_count = 0
    if bandpass:
        mag_flag_count += 1
    if _min_magnitude or _min_magnitude == 0:
        mag_flag_count += 1
    if _max_magnitude or _max_magnitude == 0:
        mag_flag_count += 1
    if mag_flag_count > 0 and mag_flag_count != 3:
        raise ValueError('The bandpass, min_magnitude and max_magnitude parameters must be used together')
    if _min_magnitude is not None:
        min_magnitude: Optional[float] = float(_min_magnitude)
    else:
        min_magnitude = None
    if _max_magnitude or _max_magnitude == 0:
        max_magnitude: Optional[float] = float(_max_magnitude)
    else:
        max_magnitude = None

    # title
    title = object_name + ' (' + proposal_code + '; ' + pi_name + ')'

    # create the finding chart
    fcs = standard_finder_charts(
        mode=mode,
        output_format=output_format,
        ra=ra,
        dec=dec,
        min_magnitude=min_magnitude,
        max_magnitude=max_magnitude,
        bandpass=bandpass,
        survey=survey,
        position_angle=pa,
        slitwidth=2 * u.arcsec,
        mos_mask_rsmt=mos_mask,
        title=title
    )
    return next(fcs)


def _parse_as_ra(s):
    """
    Parse a string as sexagesimal hours.

    Parameters
    ----------
    s : str
        String to parse.

    Returns
    -------
    Quantity
        The angle in degrees.

    """
    if s is None or s.strip() == '':
        return None
    parts = s.split(':')
    hours = _parse_as_float(parts[0])
    minutes = _parse_as_float(parts[1]) if len(parts) > 1 else 0
    seconds = _parse_as_float(parts[2]) if len(parts) > 2 else 0
    return (15 * hours + 0.25 * minutes + (15. / 3600.) * seconds) * u.deg


def parse_as_dec(s):
    """
    Parse a string as degrees.

    Parameters
    ----------
    s : str
        String to parse.

    Returns
    -------
    Quantity
        The angle in degrees.

    """

    if s is None or s.strip() == '':
        return None
    parts = s.split(':')
    sign = 1
    if parts[0].startswith('-'):
        sign = -1
        parts[0] = parts[0][1:]
    elif parts[0].startswith('+'):
        parts[0] = parts[0][1:]
    degrees = _parse_as_float(parts[0])
    arcminutes = _parse_as_float(parts[1]) if len(parts) > 1 else 0
    arcseconds = _parse_as_float(parts[2]) if len(parts) > 2 else 0
    return (sign * (degrees + arcminutes / 60. + arcseconds / 3600.)) * u.deg


def _parse_as_float(s):
    """
    Parse a string as a float, stripping a leading 0.

    Parameters
    ----------
    s : str
        String to parse.

    Returns
    -------
    float
        The float value.

    """
    s.strip()
    s.lstrip('0')
    if not s:
        s = '0'
    return float(s)
