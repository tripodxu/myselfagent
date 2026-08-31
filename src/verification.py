# HTML Feature Verification
# This module checks if generated HTML contains all required features

REQUIRED_FEATURES = {
    "navigation": ["<nav", "navbar", "nav-links"],
    "hero": ["hero", "hero-section", "#home"],
    "typing_effect": ["typed-text", "typewriter", "typing"],
    "particle_background": ["particle", "canvas", "particle-canvas"],
    "about": ["about", "about-section", "#about"],
    "skills": ["skill", "progress", "skill-bar"],
    "projects": ["project", "project-card", "filter"],
    "contact": ["contact", "form", "contact-form"],
    "footer": ["footer", "<footer"],
    "dark_mode": ["dark-mode", "theme-toggle", "data-theme"],
    "back_to_top": ["back-to-top", "scroll-top"],
    "responsive": ["@media", "max-width", "responsive"]
}

def verify_html_features(html_content: str) -> dict:
    """
    Verify if HTML contains all required features.
    
    Returns:
        dict with 'missing' list and 'present' list
    """
    missing = []
    present = []
    
    html_lower = html_content.lower()
    
    for feature, patterns in REQUIRED_FEATURES.items():
        found = any(pattern.lower() in html_lower for pattern in patterns)
        if found:
            present.append(feature)
        else:
            missing.append(feature)
    
    return {
        "missing": missing,
        "present": present,
        "total": len(REQUIRED_FEATURES),
        "passed": len(present),
        "score": len(present) / len(REQUIRED_FEATURES) * 100
    }

def get_missing_features_html(missing_features: list) -> str:
    """
    Generate HTML code for missing features using templates.
    """
    templates = {
        "navigation": '''
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
''',
        "typing_effect": '''
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
''',
        "particle_background": '''
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
''',
        "dark_mode": '''
<button id="theme-toggle" class="theme-btn">🌙</button>
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
''',
        "back_to_top": '''
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
''',
        "footer": '''
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
    }
    
    code = ""
    for feature in missing_features:
        if feature in templates:
            code += templates[feature] + "\n"
    
    return code
