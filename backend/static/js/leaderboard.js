// Count-up animation for leaderboard points
document.addEventListener('DOMContentLoaded', () => {
    const counters = document.querySelectorAll('.count-up-points');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const duration = 1200;
        const step = target / (duration / 16);
        let current = 0;
        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                counter.innerText = target;
                clearInterval(timer);
            } else {
                counter.innerText = Math.floor(current);
            }
        }, 16);
    });
});
