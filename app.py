from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import pandas as pd
from datetime import datetime
import json
import qrcode
from werkzeug.utils import secure_filename
from weasyprint import HTML

# ---------- App Configuration ----------
app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'data'
CERTIFICATE_FOLDER = 'cert_data'
QR_FOLDER = 'static/qr'
ALLOWED_EXTENSIONS = {'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USERNAME = 'admin@icem.edu.in'
ADMIN_PASSWORD = 'icem123'
CERTIFICATE_FILE = 'data/generated_certificates.xlsx'
DEPARTMENTS = {
    'Library Department': 'LIB',
    'Computer Science & Engineering': 'CSE',
    'Information Technology': 'IT',
    'Civil Engineering': 'CE',
    'Mechanical Engineering': 'ME',
    'AI & DS': 'AI',
    'First Year Engineering': 'FYE',
    'BBA Department': 'BBA',
    'MBA Department': 'MBA',
    'BCA Department': 'BCA',
    'MCA Department': 'MCA',
}
app.config['DEPARTMENTS'] = DEPARTMENTS

# ---------- Utility Functions ----------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_qr_code(cert_id, organizing_department, branch):
    # Clean up the department and branch names to avoid extra spaces
    organizing_department = organizing_department.strip()
    branch = branch.strip()
    
    # Define the path to save the QR code
    qr_folder = os.path.join(CERTIFICATE_FOLDER, organizing_department, branch, 'qr')
    os.makedirs(qr_folder, exist_ok=True)  # Ensure the directory exists

    # Generate the QR code with the base URL and certificate ID
    base_url = "http://yourbaseurl.com"  # Replace with dynamic base URL if needed
    qr_data = f"{base_url}/details/{cert_id}"
    qr_img = qrcode.make(qr_data)

    # Define the path to save the QR code image
    qr_file_path = os.path.join(qr_folder, f"{cert_id}.png")

    # Save the QR code image
    qr_img.save(qr_file_path)

    return qr_file_path

def save_certificate_metadata(data):
    cert_file = os.path.join(UPLOAD_FOLDER, 'certificates.json')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Check if the file exists and load its content
    if os.path.exists(cert_file):
        with open(cert_file, 'r') as f:
            try:
                existing = json.load(f)  # Read the existing data
            except json.JSONDecodeError:
                existing = {}  # In case of empty or corrupted file, use an empty dictionary
    else:
        existing = {}  # If the file doesn't exist, start with an empty dictionary

    # Add the new certificate data (using cert_id as the key)
    existing[data['cert_id']] = data

    # Write the updated data back to the file
    with open(cert_file, 'w') as f:
        json.dump(existing, f, indent=4)

def generate_certificate_id(department_name):
    current_year = datetime.now().year
    department_code = DEPARTMENTS.get(department_name, 'GEN')

    try:
        with open(os.path.join(UPLOAD_FOLDER, 'certificates.json'), 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    existing_ids = set(data.keys())
    serial = 1
    while True:
        serial_number = str(serial).zfill(3)
        cert_id = f"ICEM{current_year}{department_code}{serial_number}"
        if cert_id not in existing_ids:
            return cert_id
        serial += 1

def generate_pdf(template_name, context):
    html = render_template(template_name, **context)
    return HTML(string=html).write_pdf()
def save_to_excel(cert_info):
    # Check if the Excel file exists
    if os.path.exists(CERTIFICATE_FILE):
        df = pd.read_excel(CERTIFICATE_FILE)
    else:
        # Create a new DataFrame if the file doesn't exist
        df = pd.DataFrame(columns=['Certificate ID', 'Name', 'PRN', 'Branch', 'Date', 'Organizing Department', 'Status', 'File Path', 'QR Path'])

    # Add the new certificate info to the DataFrame
    new_row = {
        'Certificate ID': cert_info['cert_id'],
        'Name': cert_info['name'],
        'PRN': cert_info['prn'],
        'Branch': cert_info['branch'],
        'Date': cert_info['date'],
        'Organizing Department': cert_info['organizing_dept'],
        'Status': cert_info['status'],
        'File Path': cert_info['file_path'],
        'QR Path': cert_info['qr_path']
    }

    df = df.append(new_row, ignore_index=True)

    # Save the DataFrame to the Excel file
    df.to_excel(CERTIFICATE_FILE, index=False)
# ---------- Routes ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')
@app.route('/dashboard')
def dashboard():
    cert_file = os.path.join(UPLOAD_FOLDER, 'generated_certificates.xlsx')
    
    # Try loading certificate data from the Excel file
    try:
        cert_data = pd.read_excel(cert_file)
    except Exception:
        cert_data = pd.DataFrame()

    # Basic stats
    total_certificates = len(cert_data)
    department_counts = cert_data['Organizing Department'].value_counts().to_dict() if not cert_data.empty else {}
    recent_uploads = cert_data.tail(5).to_dict(orient='records') if not cert_data.empty else []

    # Status filter (optional)
    status_filter = request.args.get('status', '')
    if status_filter:
        cert_data = cert_data[cert_data['Status'] == status_filter]

    # Final certificate list for display
    certificate_list = cert_data.to_dict(orient='records') if not cert_data.empty else []

    return render_template(
        'dashboard.html',
        total_certificates=total_certificates,
        department_counts=department_counts,
        recent_uploads=recent_uploads,
        certificates=certificate_list,
        status_filter=status_filter
    )
@app.route('/search-certificate', methods=['GET', 'POST'])
def search_certificate():
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form['query'].strip()
        df = pd.read_excel(os.path.join(UPLOAD_FOLDER, 'generated_certificates.xlsx'))
        if query:
            results = df[(df['PRN'] == query) | (df['Name'].str.contains(query, case=False, na=False))].to_dict(orient='records')
    return render_template('search_certificate.html', results=results, query=query)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/verify')
def verify():
    return render_template('verify.html')

@app.route('/verify/<cert_id>')
def verify_by_id(cert_id):
    cert_file = os.path.join(UPLOAD_FOLDER, 'certificates.json')
    if os.path.exists(cert_file):
        with open(cert_file, 'r') as f:
            try:
                data = json.load(f)
                cert_info = data.get(cert_id)
                if cert_info:
                    return render_template('verify-by-id.html', cert=cert_info)
            except json.JSONDecodeError:
                pass
    return render_template('verify-by-id.html', cert=None, not_found=True) 
@app.route('/certificate-details', methods=['GET', 'POST'])
def certificate_details():
    if request.method == 'POST':
        cert_id = request.form.get('certificate_id', '').strip()

        if not cert_id:
            flash("⚠️ Please enter a valid Certificate ID or PRN.", "error")
            return redirect('/certificate-details')

        try:
            # Load certificate data from Excel
            df = pd.read_excel(CERTIFICATE_FILE)

            # Clean column names
            df.columns = df.columns.str.strip()

            # Search using PRN or Certificate ID if available
            if 'Certificate ID' in df.columns:
                cert_row = df[
                    (df['Certificate ID'].astype(str).str.lower() == cert_id.lower()) |
                    (df['PRN'].astype(str).str.lower() == cert_id.lower())
                ]
            else:
                cert_row = df[df['PRN'].astype(str).str.lower() == cert_id.lower()]

            if not cert_row.empty:
                cert_data = cert_row.iloc[0].to_dict()
                return render_template('details.html', cert=cert_data)
            else:
                flash("❌ Certificate not found. Please check the Certificate ID or PRN.", "error")
                return redirect('/certificate-details')

        except Exception as e:
            flash(f"🚫 Error reading certificate data: {str(e)}", "error")
            return redirect('/certificate-details')

    # GET request — simply render the search form
    return render_template('details.html')


@app.route('/download')
def download():
    return render_template('download.html')

@app.route('/download/<cert_id>')
def download_certificate(cert_id):
    cert_file = os.path.join(UPLOAD_FOLDER, 'certificates.json')
    if os.path.exists(cert_file):
        with open(cert_file, 'r') as f:
            data = json.load(f)
            cert_info = data.get(cert_id)
            if cert_info and os.path.exists(cert_info['file_path']):
                directory = os.path.dirname(cert_info['file_path'])
                filename = os.path.basename(cert_info['file_path'])
                return send_from_directory(directory, filename, as_attachment=True)
    return "Certificate not found."

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        print(f"New query from {request.form['name']} ({request.form['email']}): {request.form['message']}")
        return render_template('contact.html', success=True)
    return render_template('contact.html')

@app.route('/bulk-upload', methods=['GET', 'POST'])
def bulk_upload():
    if request.method == 'POST':
        file = request.files.get('file')
        organizing_dept = request.form.get('organizing_department')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(filepath)

            # Read the uploaded Excel file
            df = pd.read_excel(filepath)
            
            # Ensure code inside the for loop is indented properly
            for _, row in df.iterrows():
                name = row['Name']
                prn = row['PRN']
                branch = row['Branch']
                date = row['Date']

                cert_id = generate_certificate_id(organizing_dept)
                qr_path = generate_qr_code(cert_id, organizing_dept, branch)

                if organizing_dept == 'Computer Science & Engineering':
                    template = 'comp_template.html'
                    signatures = ['Issuer', 'Principal']
                elif organizing_dept == 'Library Department':
                    template = 'lib_template.html'
                    signatures = ['Issuer', 'HOD_Library', 'Principal']
                else:
                    template = 'default_template.html'
                    signatures = ['Issuer', 'Principal']

                output_folder = os.path.join(CERTIFICATE_FOLDER, organizing_dept, branch)
                os.makedirs(output_folder, exist_ok=True)

                pdf_data = generate_pdf(template, {
                    'name': name,
                    'prn': prn,
                    'date': date,
                    'qr_path': qr_path,
                    'cert_id': cert_id,
                    'signatures': signatures,
                    'branch': branch,
                    'organizing_dept': organizing_dept
                })

                pdf_path = os.path.join(output_folder, f"{cert_id}.pdf")
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_data)

                cert_info = {
                    'cert_id': cert_id,
                    'name': name,
                    'prn': prn,
                    'branch': branch,
                    'organizing_dept': organizing_dept,
                    'date': str(date),
                    'file_path': pdf_path,
                    'qr_path': qr_path,
                    'status': 'Pending'  # Default status, can be changed later
                }

                save_certificate_metadata(cert_info)

            # After the for loop completes, render the template
            return render_template('bulk-upload.html', success=True)
    
    # Render the template if GET request
    return render_template('bulk-upload.html')
@app.route('/issue-certificate')
def issue_certificate():
    # Render the certificate issuing page (replace with your template)
    return render_template('issue-certificate.html')


@app.route('/view-queries')
def view_queries():
    queries = []  # Future enhancement
    return render_template('view_queries.html', queries=queries)

@app.route('/manage')
def manage():
    return render_template('manage.html')
@app.route('/generate-certificate', methods=['POST'])
def generate_certificate():
    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        prn = request.form['prn']
        branch = request.form['branch']
        date = request.form['date']
        title = request.form['title']
        achievement = request.form['achievement']
        organizing_department = request.form['organizing_department']

        # Generate certificate ID
        cert_id = generate_certificate_id(organizing_department)

        # Generate QR code for the certificate
        qr_path = generate_qr_code(cert_id, organizing_department, branch)

        # PDF generation (you can modify this with actual templates and signatures)
        output_folder = os.path.join(CERTIFICATE_FOLDER, organizing_department, branch)
        os.makedirs(output_folder, exist_ok=True)

        pdf_data = generate_pdf('master_certificate_template.html', {
            'name': name,
            'prn': prn,
            'date': date,
            'qr_path': qr_path,
            'cert_id': cert_id,
            'signatures': ['Issuer', 'Principal'],
            'branch': branch,
            'organizing_dept': organizing_department
        })

        pdf_path = os.path.join(output_folder, f"{cert_id}.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)

        # Certificate metadata
        cert_info = {
            'cert_id': cert_id,
            'name': name,
            'prn': prn,
            'branch': branch,
            'organizing_dept': organizing_department,
            'date': str(date),
            'file_path': pdf_path,
            'qr_path': qr_path,
            'status': 'Pending'  # Default status
        }

        # Save certificate metadata to JSON
        save_certificate_metadata(cert_info)

        # Save certificate data to Excel
        save_to_excel(cert_info)

        # Return the success template with the certificate information
        return render_template('certificate_issued.html', certificate=cert_info)

    return render_template('issue-certificate.html')
  # Adjust if needed

# ---------- Run the App ----------
if __name__ == '__main__':
    app.run(debug=True)