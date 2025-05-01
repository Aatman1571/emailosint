from flask import Flask, redirect, url_for, g , make_response , session
from flask import render_template
from flask import request
from functools import wraps
from flask_login import login_required

from email.parser import HeaderParser
import time
import dateutil.parser

from datetime import datetime, timedelta
import re

import pygal
from pygal.style import Style

from IPy import IP
import geoip2.database

import argparse
import spamcheck
import requests
import subprocess
import sqlite3
from email.parser import Parser
from intelxapi import intelx




conn = sqlite3.connect('user.db')
c = conn.cursor()
cursor = conn.cursor()


# Create a table to store user information if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, email TEXT)''')
conn.commit()


app = Flask(__name__)
app.secret_key = 'GTU'
reader = geoip2.database.Reader(
    '%s/data/GeoLite2-Country.mmdb' % app.static_folder)

DATABASE = 'user.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
    return g.db

@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint not in allowed_routes and 'name' not in session:
        return redirect('/')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'name' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        
        # connect to the database
        conn = sqlite3.connect('user.db')
        c = conn.cursor()
        
        # check if user exists in database and password matches
        c.execute('SELECT * FROM user WHERE name = ? AND password = ?', (name, password))
        user = c.fetchone()
        
        if user is not None:
            session['name'] = user[1]  # Store the username in the session
            return redirect(url_for('dashboard'))
        else:
            # show error message
            error = 'Invalid credentials. Please try again.'
            return render_template('login.html', error=error)
    else:
        # show login form
        return render_template('login.html')
    
@app.route('/dashboard')
def dashboard():
    # Check if user is logged in
    if 'name' not in session:
        return redirect('/')
    
    # Render the dashboard template
    return render_template('dashboard.html')

@app.route('/emailosint', methods=['GET', 'POST'])
def emailosint():
    # Check if user is logged in
    if 'name' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        intelx_api_key = '42c6a36b-8e74-4498-9bb4-f001dc8f15e9'
        intelx_api = intelx(intelx_api_key)
        intelx_results = []
        results = intelx_api.search(email)
        if results['records']:
            names = [re.sub(r"\[Part \d+ of \d+\]", "", record['name']) for record in results['records']]
            message = {
                'email': email,
                'records': names
            }
            intelx_results.append(message)
        else:
            message = {
                'email': email,
                'records': []
            }
            intelx_results.append(message)

        
        # Run the holehe search
        holehe_results = []
        try:
            cmd_output = subprocess.check_output(['holehe', '--only-used', email])
            filtered_output = [line.strip() for line in cmd_output.decode().split('\n') if '+' in line and 'Email' not in line]
            for line in filtered_output:
                website = line.split()[1]
                holehe_results.append({'email': email, 'website': website})
        except subprocess.CalledProcessError as e:
            error_message = f"Error running holehe for email address {email}: {e}"
            # Do something with the error message (e.g. log it)
        
        # Render the results template, passing in the intelx and holehe results
        return render_template('emailosint.html', intelx_results=intelx_results, holehe_results=holehe_results)
    
    # Render the page2 template for GET requests
    return render_template('emailosint.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('user.db')
        c = conn.cursor()
        c.execute("INSERT INTO user (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('register.html')

@app.route('/redirect-login', methods=['GET'])
def redirect_login():
    return redirect('/')

@app.route('/logout')
def logout():
    # clear the session and redirect to login page
    session.pop('name', None)
    response = make_response(redirect('/'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = 0
    response.headers['Pragma'] = 'no-cache'
    response.headers['Last-Modified'] = datetime.now() - timedelta(days=365)
    return response

@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.context_processor
def utility_processor():
    def getCountryForIP(line):
        ipv4_address = re.compile(r"""
            \b((?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d))\b""", re.X)
        ip = ipv4_address.findall(line)
        if ip:
            ip = ip[0]  # take the 1st ip and ignore the rest
            if IP(ip).iptype() == 'PUBLIC':
                r = reader.country(ip).country
                if r.iso_code and r.name:
                    return {
                        'iso_code': r.iso_code.lower(),
                        'country_name': r.name
                    }
    return dict(country=getCountryForIP)


@app.context_processor
def utility_processor():
    def duration(seconds, _maxweeks=99999999999):
        return ', '.join(
            '%d %s' % (num, unit)
            for num, unit in zip([
                (seconds // d) % m
                for d, m in (
                    (604800, _maxweeks),
                    (86400, 7), (3600, 24),
                    (60, 60), (1, 60))
            ], ['wk', 'd', 'hr', 'min', 'sec'])
            if num
        )
    return dict(duration=duration)

def spamcheck(mail_data):
    api_key = 'f2783038-950f-4f61-a05c-4bc222f4d91b'
    url = 'https://spamcheck.postmarkapp.com/filter'

    # Get the email content from the request
    mail_data = request.form['headers']

    # Make a POST request to the Spamcheck API
    response = requests.post(url, data={'email': mail_data}, headers={'X-Postmark-Server-Token': api_key})

    # Check the response status code
    if response.status_code == 200:
        # Get the Spamcheck score from the response
        score = response.json()['score']
        return f'{score}'
    else:
        return 'Error: Failed to check spam'

def dateParser(line):
    try:
        r = dateutil.parser.parse(line, fuzzy=True)
    except ValueError:
        r = re.findall('^(.*?)\s*(?:\(|utc)', line, re.I)
        if r:
            r = dateutil.parser.parse(r[0])
    return r


def getHeaderVal(h, data, rex='\s*(.*?)\n\S+:\s'):
    r = re.findall('%s:%s' % (h, rex), data, re.X | re.DOTALL | re.I)
    if r:
        val = r[0].strip()
        if h.lower() == 'from':
            # check if this is a forwarded message and extract From address if available
            if '----- Forwarded message -----' in data:
                fwd_data = data.split('----- Forwarded message -----')[1]
                fwd_from = getHeaderVal('From', fwd_data)
                if fwd_from:
                    val += ' (forwarded from: ' + fwd_from + ')'
        return val
    else:
        return None


    
def is_spoofed(header):
    # Extract sender domain
    sender_domain = re.findall(r"@[\w\.-]+", header['From'])[0][1:]
    
    # Check if SPF and DKIM are present
    if header.get('SPF') and header.get('DKIM-Signature'):
        # Check if SPF and DKIM both pass
        if header['SPF'].startswith('Pass') and header['DKIM-Signature'].startswith('Pass'):
            # Extract domain from DKIM signature
            dkim_domain = re.findall(r" d=([\w\.-]+)", header['DKIM-Signature'])[0]
            if sender_domain == dkim_domain:
                return "Email is not spoofed"
            else:
                return "Email may be spoofed"
        else:
            return "Email may be spoofed"
    else:
        # If SPF and DKIM are not present, check if there are other authentication mechanisms
        for key, value in header.items():
            if key.startswith('Authentication-Results'):
                if 'spf=pass' in value.lower() or 'dkim=pass' in value.lower():
                    return "Email may not be spoofed"
                else:
                    return "Email may be spoofed"
        # No authentication mechanisms found
        return "Email may be spoofed"

@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if 'name' not in session:  # Check if user is not logged in
        return redirect('/')  # Redirect to login page
    if request.method == 'POST':
        mail_data = request.form['headers'].strip()
        r = {}
        n = HeaderParser().parsestr(mail_data)
        graph = []
        received = n.get_all('Received')
        header = Parser().parsestr(mail_data)
        spf_result = re.search('SPF=(pass|fail|softfail|neutral)', mail_data, flags=re.IGNORECASE)
        spf_result = spf_result.group(1).lower() if spf_result else 'Missing'
        # Extract DKIM pass/fail status
        dkim_result = re.search('DKIM=(pass|fail)', mail_data, flags=re.IGNORECASE)
        dkim_result = dkim_result.group(1).lower() if dkim_result else 'Missing'
        # Extract DMARC pass/fail status
        dmarc_result = re.search('DMARC=(pass|fail|quarantine)', mail_data, flags=re.IGNORECASE)
        dmarc_result = dmarc_result.group(1).lower() if dmarc_result else 'Missing'
        isSpoofed = is_spoofed(header)
        score = spamcheck(mail_data)
        intelx_api_key = '42c6a36b-8e74-4498-9bb4-f001dc8f15e9'
        intelx_api = intelx(intelx_api_key)
        from_pattern = re.compile(r"[\w\.-]+@[\w\.-]+")
        to_pattern = re.compile(r"To:\s*([\w\.\-]+@[\w\.\-]+)")
        from_email_match = from_pattern.search(n.get('From') or getHeaderVal('From', mail_data))
        if from_email_match:
            from_email = from_email_match.group(0)
        else:
            from_email = None
        print(from_email)
        to_email_match = to_pattern.search(mail_data)
        if to_email_match:
            to_email = to_email_match.group(1)
        else:
            to_email = None

        email_addresses = [email for email in [from_email, to_email] if email is not None]
        # intelx_results = []
        # for email in email_addresses:
        #     results = intelx_api.search(email)
        #     if results['records']:
        #         names = [record['name'] for record in results['records']]
        #         message = {
        #             'email': email,
        #             'records': names
        #         }
        #         intelx_results.append(message)
        #     else:
        #         message = {
        #             'email': email,
        #             'records': []
        #         }
        #         intelx_results.append(message)



        holehe_results = []

        for email in email_addresses:
            try:
                cmd_output = subprocess.check_output(['holehe', '--only-used', email])
                filtered_output = [line.strip() for line in cmd_output.decode().split('\n') if '+' in line and 'Email' not in line]
                for line in filtered_output:
                    website = line.split()[1]
                    holehe_results.append({'email': email, 'website': website})
            except subprocess.CalledProcessError as e:
                error_message = f"Error running holehe for email address {email}: {e}"


        if received:
            received = [i for i in received if ('from' in i or 'by' in i)]
        else:
            received = re.findall(
                'Received:\s*(.*?)\n\S+:\s+', mail_data, re.X | re.DOTALL | re.I)
        c = len(received)
        for i in range(len(received)):
            if ';' in received[i]:
                line = received[i].split(';')
            else:
                line = received[i].split('\r\n')
            line = list(map(str.strip, line))
            line = [x.replace('\r\n', ' ') for x in line]
            try:
                if ';' in received[i + 1]:
                    next_line = received[i + 1].split(';')
                else:
                    next_line = received[i + 1].split('\r\n')
                next_line = list(map(str.strip, next_line))
                next_line = [x.replace('\r\n', '') for x in next_line]
            except IndexError:
                next_line = None

            org_time = dateParser(line[-1])
            if not next_line:
                next_time = org_time
            else:
                next_time = dateParser(next_line[-1])

            if line[0].startswith('from'):
                data = re.findall(
                    """
                    from\s+
                    (.*?)\s+
                    by(.*?)
                    (?:
                        (?:with|via)
                        (.*?)
                        (?:\sid\s|$)
                        |\sid\s|$
                    )""", line[0], re.DOTALL | re.X)
            else:
                data = re.findall(
                    """
                    ()by
                    (.*?)
                    (?:
                        (?:with|via)
                        (.*?)
                        (?:\sid\s|$)
                        |\sid\s
                    )""", line[0], re.DOTALL | re.X)

            delay = (org_time - next_time).seconds
            if delay < 0:
                delay = 0

            try:
                ftime = org_time.utctimetuple()
                ftime = time.strftime('%m/%d/%Y %I:%M:%S %p', ftime)
                r[c] = {
                    'Timestmp': org_time,
                    'Time': ftime,
                    'Delay': delay,
                    'Direction': [x.replace('\n', ' ') for x in list(map(str.strip, data[0]))]
                }
                c -= 1
            except IndexError:
                pass

        for i in list(r.values()):
            if i['Direction'][0]:
                graph.append(["From: %s" % i['Direction'][0], i['Delay']])
            else:
                graph.append(["By: %s" % i['Direction'][1], i['Delay']])

        totalDelay = sum([x['Delay'] for x in list(r.values())])
        fTotalDelay = utility_processor()['duration'](totalDelay)
        delayed = True if totalDelay else False

        custom_style = Style(
            background='transparent',
            plot_background='transparent',
            font_family='googlefont:Open Sans',
            # title_font_size=12,
        )
        line_chart = pygal.HorizontalBar(
            style=custom_style, height=250, legend_at_bottom=True,
            tooltip_border_radius=10)
        line_chart.tooltip_fancy_mode = False
        line_chart.title = 'Total Delay is: %s' % fTotalDelay
        line_chart.x_title = 'Delay in seconds.'
        for i in graph:
            line_chart.add(i[0], i[1])
        chart = line_chart.render(is_unicode=True)

        summary = {
            'From': n.get('From') or getHeaderVal('from', mail_data),
            'To': n.get('to') or getHeaderVal('to', mail_data),
            'Cc': n.get('cc') or getHeaderVal('cc', mail_data),
            'Subject': n.get('Subject') or getHeaderVal('Subject', mail_data),
            'MessageID': n.get('Message-ID') or getHeaderVal('Message-ID', mail_data),
            'Date': n.get('Date') or getHeaderVal('Date', mail_data),
        }

        if '----- Forwarded message -----' in mail_data:
            fwd_data = mail_data.split('----- Forwarded message -----')[1]
            fwd_from = getHeaderVal('From', fwd_data)
            if fwd_from:
                summary['From'] += ' (forwarded from: ' + fwd_from + ')'

        security_headers = ['Received-SPF', 'Authentication-Results',
                            'DKIM-Signature', 'ARC-Authentication-Results']

        return render_template(
            'index.html', data=r, delayed=delayed, summary=summary,
            n=n, chart=chart, security_headers=security_headers,score = score, holehe_results = holehe_results, isSpoofed=isSpoofed, spf_result=spf_result, dkim_result=dkim_result, dmarc_result=dmarc_result)
            # intelx_results=intelx_results)
    else:
        return render_template('index.html')
        
    



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Mail Header Analyser")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                        help="Enable debug mode")
    parser.add_argument("-b", "--bind", default="127.0.0.1", type=str)
    parser.add_argument("-p", "--port", default="8080", type=int)
    args = parser.parse_args()

    app.debug =True
    app.run(host=args.bind, port=args.port)
