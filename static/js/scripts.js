
document.addEventListener('DOMContentLoaded', function () {
    const slides = document.querySelectorAll('.testimonial-item');
    const dots = document.querySelectorAll('.dot');
    let currentSlide = 0;
    const totalSlides = slides.length;

    function showSlide(n) {
       
        slides.forEach(slide => slide.classList.remove('active'));
        dots.forEach(dot => dot.classList.remove('active'));

        
        currentSlide = (n + totalSlides) % totalSlides;
        slides[currentSlide].classList.add('active');
        dots[currentSlide].classList.add('active');
    }

    function nextSlide() {
        showSlide(currentSlide + 1);
    }

  
    dots.forEach((dot, i) => {
        dot.addEventListener('click', () => showSlide(i));
    });

   
    setInterval(nextSlide, 5000);

    
    showSlide(0);
});