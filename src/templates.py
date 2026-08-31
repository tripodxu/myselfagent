# HTML Feature Templates
# These templates can be used to supplement missing features in generated HTML

NAVIGATION_BAR = '''
<nav id="navbar">
    <div class="nav-container">
        <a href="#" class="logo">Portfolio</a>
        <ul class="nav-links">
            <li><a href="#home">Home</a></li>
            <li><a href="#about">About</a></li>
            <li><a href="#skills">Skills</a></li>
            <li><a href="#projects">Projects</a></li>
            <li><a href="#contact">Contact</a></li>
        </ul>
        <button id="theme-toggle" class="theme-btn">🌙</button>
        <div class="hamburger">☰</div>
    </div>
</nav>
'''

TYPING_EFFECT = '''
<span id="typed-text"></span>
<script>
const typedText = document.getElementById('typed-text');
const words = ["Web Developer", "Designer", "Creator"];
let wordIndex = 0, charIndex = 0, isDeleting = false;
function type() {
    const current = words[wordIndex];
    typedText.textContent = isDeleting 
        ? current.substring(0, charIndex - 1) 
        : current.substring(0, charIndex + 1);
    charIndex += isDeleting ? -1 : 1;
    if (!isDeleting && charIndex === current.length) {
        isDeleting = true;
        setTimeout(type, 1500);
    } else if (isDeleting && charIndex === 0) {
        isDeleting = false;
        wordIndex = (wordIndex + 1) % words.length;
        setTimeout(type, 500);
    } else {
        setTimeout(type, isDeleting ? 50 : 100);
    }
}
type();
</script>
'''

PARTICLE_BACKGROUND = '''
<canvas id="particle-canvas"></canvas>
<script>
const canvas = document.getElementById('particle-canvas');
const ctx = canvas.getContext('2d');
let particles = [];
function resizeCanvas() {
    canvas.width = canvas.parentElement.offsetWidth;
    canvas.height = canvas.parentElement.offsetHeight;
}
function initParticles() {
    particles = [];
    for (let i = 0; i < 50; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            radius: Math.random() * 2 + 1,
            vx: Math.random() * 2 - 1,
            vy: Math.random() * 2 - 1
        });
    }
}
function drawParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.fill();
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
    });
    requestAnimationFrame(drawParticles);
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();
initParticles();
drawParticles();
</script>
'''

DARK_MODE_TOGGLE = '''
<script>
const themeBtn = document.getElementById('theme-toggle');
const currentTheme = localStorage.getItem('theme');
if (currentTheme === 'dark') {
    document.body.setAttribute('data-theme', 'dark');
    themeBtn.textContent = '☀️';
}
themeBtn.addEventListener('click', () => {
    if (document.body.getAttribute('data-theme') === 'dark') {
        document.body.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        themeBtn.textContent = '🌙';
    } else {
        document.body.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        themeBtn.textContent = '☀️';
    }
});
</script>
'''

BACK_TO_TOP = '''
<button id="back-to-top" class="back-to-top">↑</button>
<script>
const backToTopBtn = document.getElementById('back-to-top');
window.addEventListener('scroll', () => {
    backToTopBtn.classList.toggle('visible', window.scrollY > 300);
});
backToTopBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});
</script>
'''

SKILL_BAR = '''
<div class="skill-bar">
    <div class="skill-info">
        <span>{skill_name}</span>
        <span>{percentage}%</span>
    </div>
    <div class="progress">
        <div class="progress-bar" style="--progress: {percentage}%"></div>
    </div>
</div>
'''

TESTIMONIAL_CAROUSEL = '''
<div class="testimonial-carousel">
    <div class="testimonial-track">
        <div class="testimonial">
            <div class="stars">★★★★★</div>
            <p>"Great work!"</p>
            <div class="author">
                <img src="avatar.jpg" alt="Avatar">
                <div>
                    <strong>John Doe</strong>
                    <span>CEO, Company</span>
                </div>
            </div>
        </div>
    </div>
    <button class="prev">❮</button>
    <button class="next">❯</button>
</div>
'''

MULTI_STEP_FORM = '''
<form id="multi-step-form">
    <div class="form-step active" data-step="1">
        <h3>Step 1: Personal Info</h3>
        <input type="text" placeholder="Name" required>
        <input type="email" placeholder="Email" required>
        <button type="button" class="next-btn" data-next="2">Next</button>
    </div>
    <div class="form-step" data-step="2">
        <h3>Step 2: Project Details</h3>
        <select><option>Web Development</option><option>Mobile App</option></select>
        <textarea placeholder="Description"></textarea>
        <button type="button" class="prev-btn" data-prev="1">Back</button>
        <button type="button" class="next-btn" data-next="3">Next</button>
    </div>
    <div class="form-step" data-step="3">
        <h3>Step 3: Submit</h3>
        <div class="file-upload">
            <input type="file" id="file-input">
            <label for="file-input">Drop files here or click to upload</label>
        </div>
        <button type="button" class="prev-btn" data-prev="2">Back</button>
        <button type="submit">Submit</button>
    </div>
</form>
'''

FILE_UPLOAD = '''
<div class="file-upload" id="file-upload">
    <input type="file" id="file-input" multiple>
    <label for="file-input">
        <span class="upload-icon">📁</span>
        <span>Drop files here or click to upload</span>
    </label>
</div>
<script>
const fileUpload = document.getElementById('file-upload');
const fileInput = document.getElementById('file-input');
fileUpload.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileUpload.classList.add('dragover');
});
fileUpload.addEventListener('dragleave', () => {
    fileUpload.classList.remove('dragover');
});
fileUpload.addEventListener('drop', (e) => {
    e.preventDefault();
    fileUpload.classList.remove('dragover');
    const files = e.dataTransfer.files;
    console.log('Files dropped:', files);
});
fileInput.addEventListener('change', () => {
    console.log('Files selected:', fileInput.files);
});
</script>
'''

FOOTER = '''
<footer>
    <div class="social-links">
        <a href="#"><i class="fab fa-github"></i></a>
        <a href="#"><i class="fab fa-linkedin"></i></a>
        <a href="#"><i class="fab fa-twitter"></i></a>
        <a href="#"><i class="fab fa-weixin"></i></a>
    </div>
    <p>&copy; 2024 Portfolio. All rights reserved.</p>
</footer>
'''

# CSS for common features
CSS_DARK_MODE = '''
[data-theme="dark"] {
    --bg-color: #1a1a1a;
    --text-color: #eee;
    --card-bg: #333;
}
'''

CSS_BACK_TO_TOP = '''
.back-to-top {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 40px;
    height: 40px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s;
}
.back-to-top.visible {
    opacity: 1;
    visibility: visible;
}
'''

CSS_SKILL_BAR = '''
.skill-bar {
    margin-bottom: 1rem;
}
.skill-info {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
}
.progress {
    height: 10px;
    background: #e0e0e0;
    border-radius: 5px;
    overflow: hidden;
}
.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--primary), var(--accent));
    border-radius: 5px;
    width: var(--progress);
    transition: width 1s ease;
}
'''

CSS_TESTIMONIAL = '''
.testimonial-carousel {
    position: relative;
    max-width: 600px;
    margin: 0 auto;
    overflow: hidden;
}
.testimonial {
    text-align: center;
    padding: 2rem;
}
.stars {
    color: #f59e0b;
    font-size: 1.5rem;
    margin-bottom: 1rem;
}
.author {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    margin-top: 1rem;
}
.author img {
    width: 50px;
    height: 50px;
    border-radius: 50%;
}
'''

CSS_MULTI_STEP_FORM = '''
.form-step {
    display: none;
}
.form-step.active {
    display: block;
}
'''

CSS_FILE_UPLOAD = '''
.file-upload {
    border: 2px dashed #ccc;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;
}
.file-upload.dragover {
    border-color: var(--primary);
    background: rgba(99, 102, 241, 0.1);
}
.file-upload input[type="file"] {
    display: none;
}
'''
