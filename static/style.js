document.addEventListener('DOMContentLoaded', function () {

    // ✅ FIX: Set today's date on any date input — safe على كل الصفحات
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];
    dateInputs.forEach(function (input) {
        if (!input.value) {
            input.value = today;
        }
    });

    // ✅ FIX: Navbar scroll effect — بيتحقق إن navbar موجود الأول
    const nav = document.getElementById('navbar');
    if (nav) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 20) {
                nav.classList.add('nav-scrolled');
            } else {
                nav.classList.remove('nav-scrolled');
            }
        });
    }

});