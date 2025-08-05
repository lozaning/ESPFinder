from flask import Flask, render_template, send_file, request, jsonify, Response
import os
import subprocess
import json
from datetime import datetime
from ..database.database import db
from ..database.models import Product, PDF, Photo
from ..config import Config

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

@app.route('/')
def index():
    session = db.get_session()
    try:
        total_products = session.query(Product).count()
        total_photos = session.query(Photo).count()
        recent_products = session.query(Product).order_by(Product.created_at.desc()).limit(10).all()
        
        return render_template('index.html', 
                             total_products=total_products,
                             total_photos=total_photos,
                             recent_products=recent_products)
    finally:
        session.close()

@app.route('/products')
def products():
    session = db.get_session()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        products_query = session.query(Product).order_by(Product.created_at.desc())
        products = products_query.offset((page - 1) * per_page).limit(per_page).all()
        total = products_query.count()
        
        return render_template('products.html', 
                             products=products,
                             page=page,
                             per_page=per_page,
                             total=total)
    finally:
        session.close()

@app.route('/product/<fcc_id>')
def product_detail(fcc_id):
    session = db.get_session()
    try:
        product = session.query(Product).filter_by(fcc_id=fcc_id).first()
        if not product:
            return "Product not found", 404
            
        return render_template('product_detail.html', product=product)
    finally:
        session.close()

@app.route('/photos')
def photos():
    session = db.get_session()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 24
        
        photos_query = session.query(Photo).order_by(Photo.created_at.desc())
        photos = photos_query.offset((page - 1) * per_page).limit(per_page).all()
        total = photos_query.count()
        
        return render_template('photos.html', 
                             photos=photos,
                             page=page,
                             per_page=per_page,
                             total=total)
    finally:
        session.close()

@app.route('/image/<int:photo_id>')
def serve_image(photo_id):
    session = db.get_session()
    try:
        photo = session.query(Photo).get(photo_id)
        if not photo or not os.path.exists(photo.local_path):
            return "Image not found", 404
            
        return send_file(photo.local_path, mimetype='image/png')
    finally:
        session.close()

@app.route('/thumbnail/<int:photo_id>')
def serve_thumbnail(photo_id):
    session = db.get_session()
    try:
        photo = session.query(Photo).get(photo_id)
        if not photo or not os.path.exists(photo.local_path):
            return "Image not found", 404
        
        from PIL import Image
        
        thumb_dir = os.path.join(os.path.dirname(photo.local_path), 'thumbnails')
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, f"thumb_{os.path.basename(photo.local_path)}")
        
        if not os.path.exists(thumb_path):
            with Image.open(photo.local_path) as img:
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                img.save(thumb_path, "PNG")
        
        return send_file(thumb_path, mimetype='image/png')
    finally:
        session.close()

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return render_template('search.html', products=[], photos=[], query='')
    
    session = db.get_session()
    try:
        products = session.query(Product).filter(
            (Product.fcc_id.contains(query)) |
            (Product.applicant.contains(query)) |
            (Product.product_name.contains(query))
        ).limit(50).all()
        
        photos = session.query(Photo).join(Product).filter(
            (Product.fcc_id.contains(query)) |
            (Product.applicant.contains(query)) |
            (Product.product_name.contains(query))
        ).limit(50).all()
        
        return render_template('search.html', 
                             products=products, 
                             photos=photos, 
                             query=query)
    finally:
        session.close()

@app.route('/logs')
def logs_page():
    return render_template('logs.html')

@app.route('/api/logs')
def api_logs():
    lines = request.args.get('lines', 100, type=int)
    container = request.args.get('container', 'espfinder')
    
    try:
        cmd = ['docker', 'logs', '--tail', str(lines), container]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logs = result.stdout + result.stderr
            return jsonify({
                'success': True,
                'logs': logs,
                'container': container
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Docker logs failed: {result.stderr}',
                'container': container
            })
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Timeout getting logs',
            'container': container
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'container': container
        })

@app.route('/debug/logs')
def debug_logs():
    """Plain text logs endpoint for remote debugging"""
    lines = request.args.get('lines', 200, type=int)
    container = request.args.get('container', 'espfinder')
    
    try:
        cmd = ['docker', 'logs', '--tail', str(lines), container]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        response_text = f"=== LOGS FOR CONTAINER: {container} ===\n"
        response_text += f"=== LAST {lines} LINES ===\n"
        response_text += f"=== COMMAND: {' '.join(cmd)} ===\n\n"
        
        if result.returncode == 0:
            logs = result.stdout + result.stderr
            response_text += logs if logs.strip() else "No logs available"
        else:
            response_text += f"ERROR: {result.stderr}"
            
        return Response(response_text, mimetype='text/plain')
        
    except Exception as e:
        return Response(f"ERROR: {str(e)}", mimetype='text/plain')

@app.route('/api/logs/stream')
def stream_logs():
    container = request.args.get('container', 'espfinder')
    
    def generate():
        try:
            cmd = ['docker', 'logs', '-f', '--tail', '50', container]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield f"data: {json.dumps({'log': line.rstrip(), 'container': container})}\n\n"
                    
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/plain')

@app.route('/api/containers')
def api_containers():
    try:
        cmd = ['docker', 'ps', '--format', 'json']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    container_info = json.loads(line)
                    containers.append({
                        'name': container_info.get('Names', ''),
                        'status': container_info.get('Status', ''),
                        'image': container_info.get('Image', '')
                    })
            
            return jsonify({
                'success': True,
                'containers': containers
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/trigger-scrape')
def trigger_scrape():
    try:
        cmd = ['docker', 'exec', 'espfinder', 'python', '-m', 'src.main']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Scraper timeout (>60s)'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/debug/scrape')
def debug_scrape():
    """Plain text scrape trigger for remote debugging"""
    try:
        cmd = ['docker', 'exec', 'espfinder', 'python', '-m', 'src.main']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        response_text = f"=== MANUAL SCRAPE EXECUTION ===\n"
        response_text += f"=== COMMAND: {' '.join(cmd)} ===\n"
        response_text += f"=== EXIT CODE: {result.returncode} ===\n\n"
        
        if result.stdout:
            response_text += "=== STDOUT ===\n"
            response_text += result.stdout + "\n\n"
            
        if result.stderr:
            response_text += "=== STDERR ===\n" 
            response_text += result.stderr + "\n\n"
            
        response_text += f"=== EXECUTION COMPLETED ===\n"
        
        return Response(response_text, mimetype='text/plain')
        
    except subprocess.TimeoutExpired:
        return Response("ERROR: Scraper execution timeout (>120s)", mimetype='text/plain')
    except Exception as e:
        return Response(f"ERROR: {str(e)}", mimetype='text/plain')

@app.route('/debug/status')
def debug_status():
    """Plain text system status for remote debugging"""
    try:
        response_text = "=== ESPFINDER SYSTEM STATUS ===\n\n"
        
        # Database stats
        session = db.get_session()
        try:
            total_products = session.query(Product).count()
            total_photos = session.query(Photo).count()
            total_pdfs = session.query(PDF).count()
            processed_pdfs = session.query(PDF).filter_by(processed=True).count()
            downloaded_pdfs = session.query(PDF).filter_by(downloaded=True).count()
            
            response_text += "=== DATABASE STATS ===\n"
            response_text += f"Products: {total_products}\n"
            response_text += f"Photos: {total_photos}\n"
            response_text += f"PDFs Total: {total_pdfs}\n"
            response_text += f"PDFs Downloaded: {downloaded_pdfs}\n"
            response_text += f"PDFs Processed: {processed_pdfs}\n\n"
            
            # Recent products
            recent_products = session.query(Product).order_by(Product.created_at.desc()).limit(5).all()
            if recent_products:
                response_text += "=== RECENT PRODUCTS ===\n"
                for product in recent_products:
                    response_text += f"{product.fcc_id} - {product.applicant} - {len(product.photos)} photos\n"
                response_text += "\n"
                
        finally:
            session.close()
        
        # Container status
        try:
            cmd = ['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Image}}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                response_text += "=== CONTAINER STATUS ===\n"
                response_text += result.stdout + "\n"
            else:
                response_text += f"=== CONTAINER STATUS ERROR ===\n{result.stderr}\n\n"
        except Exception as e:
            response_text += f"=== CONTAINER STATUS ERROR ===\n{str(e)}\n\n"
            
        # File system check
        try:
            data_dir = Config.DATA_DIR
            response_text += "=== FILE SYSTEM ===\n"
            response_text += f"Data directory: {data_dir}\n"
            
            if os.path.exists(data_dir):
                response_text += f"Data dir exists: Yes\n"
                
                db_path = os.path.join(data_dir, 'database')
                img_path = os.path.join(data_dir, 'images')
                
                response_text += f"Database dir exists: {os.path.exists(db_path)}\n"
                response_text += f"Images dir exists: {os.path.exists(img_path)}\n"
                
                if os.path.exists(img_path):
                    image_dirs = [d for d in os.listdir(img_path) if os.path.isdir(os.path.join(img_path, d))]
                    response_text += f"FCC ID directories: {len(image_dirs)}\n"
                    if image_dirs:
                        response_text += f"Sample directories: {image_dirs[:5]}\n"
            else:
                response_text += f"Data dir exists: No\n"
                
        except Exception as e:
            response_text += f"=== FILE SYSTEM ERROR ===\n{str(e)}\n\n"
        
        return Response(response_text, mimetype='text/plain')
        
    except Exception as e:
        return Response(f"ERROR: {str(e)}", mimetype='text/plain')

@app.route('/api/stats')
def api_stats():
    session = db.get_session()
    try:
        total_products = session.query(Product).count()
        total_photos = session.query(Photo).count()
        total_pdfs = session.query(PDF).count()
        
        processed_pdfs = session.query(PDF).filter_by(processed=True).count()
        downloaded_pdfs = session.query(PDF).filter_by(downloaded=True).count()
        
        return jsonify({
            'total_products': total_products,
            'total_photos': total_photos,
            'total_pdfs': total_pdfs,
            'processed_pdfs': processed_pdfs,
            'downloaded_pdfs': downloaded_pdfs
        })
    finally:
        session.close()

if __name__ == '__main__':
    Config.ensure_dirs()
    db.create_tables()
    app.run(host='0.0.0.0', port=5000, debug=True)