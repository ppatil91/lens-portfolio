# 📸 Lens - Photographer Portfolio & Community

A beautiful, full-stack web application built for photographers to showcase their work, track their performance, and connect with other creators. 

*Built with Flask, TailwindCSS, Chart.js, and Flask-SocketIO (for that sweet instant messaging).*

---

## 🚀 Features

### 1. 🖼️ Stunning Portfolios & Masonry Grid
- Upload your best shots showcasing EXIF data, categories, and tags.
- Fully responsive masonry grid layout that looks amazing on any screen size.
- **HEIC Support**: Automatically converts iPhone `.heic` photos to `.jpeg` under the hood! (Apple wale hamesha alag hi chalte hain yaar...)
- Auto-compression and resizing for massive images to keep load times snappy.

### 2. 💬 Real-Time Direct Messaging (WebSockets)
- **True Instant Chat**: Built with `Flask-SocketIO` for sub-millisecond, real-time message delivery. No clunky page reloads or HTTP polling!
- **Inbox Interface**: Organizes your conversations, puts the latest ones on top, and shows an animated unread badge when someone slides into your DMs.
- "Message" buttons integrated directly onto user profiles and sidebars.

### 3. 📈 Performance Analytics Dashboard
- **Chart.js Integration**: See exactly how your photos are performing with a clean, animated Bar Chart comparing **Views vs. Likes**.
- Tracks top 10 most popular photos giving you insights into what your audience actually likes.

### 4. 🔗 Social Connectivity
- Follow other creators and build your custom Home Feed.
- Save/Bookmark photos from others to use as inspiration later.
- Explore page with trending tags to find new styles.
- **AJAX Interactions**: Liking, Saving, and Commenting all happen silently in the background without refreshing the page.

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Flask-SQLAlchemy (SQLite)
- **Real-Time Engine**: Flask-SocketIO, Eventlet
- **Frontend**: HTML5, Jinja2, Vanilla JavaScript
- **Styling**: TailwindCSS (via CDN for raw speed) & Phosphor Icons
- **Image Processing**: Pillow & Pillow_HEIF

---

## 💻 How to Run Locally

Want to spin this up on your own machine? It's super easy.

1. **Clone the repo**
   ```bash
   git clone https://github.com/ppatil91/lens-portfolio.git
   cd lens-portfolio
   ```

2. **Create a virtual environment (Optional but Recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Magic!**
   ```bash
   # We use SocketIO, so the standard flask run won't give you real-time features.
   # Run the python file directly!
   python3 run.py
   ```

5. Go to `http://localhost:5000` in your browser and start exploring!

---

## 🤫 Developer Notes
> *I've sprinkled some authentic Hindi/English developer comments throughout the codebase (`run.py`, `models.py`) to give it that true "homebrew" feel. Keep an eye out for them while reading the code!* 😉

**Database Ready Hai!**
