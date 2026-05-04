const authContainer = document.getElementById('auth-buttons');
    const isLoggedIn = localStorage.getItem('isLoggedIn');

    if (isLoggedIn === 'true') {
        authContainer.innerHTML = `
            <a href="dashboard.html" style="text-decoration: none;">
                <button class="btn" style="margin-right: 10px;">Go to Dashboard</button>
            </a>
            <button class="btn btn-logout" onclick="logout()">Log Out</button>
        `;
    }

    function logout() {
        localStorage.removeItem('isLoggedIn'); 
        window.location.reload(); 
    }
    document.getElementById('loginForm').onsubmit = function(e) {
        e.preventDefault();
        localStorage.setItem('isLoggedIn', 'true'); 
        window.location.href = 'dashboard.html'; 
    };
    function logout() {
        localStorage.removeItem('isLoggedIn');
        window.location.href = 'home.html';
    }
    document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('incomeDate');
    
    const today = new Date();
    const yyyy = today.getFullYear();
    let mm = today.getMonth() + 1; 
    let dd = today.getDate();

    if (dd < 10) dd = '0' + dd;
    if (mm < 10) mm = '0' + mm;

    const formattedToday = yyyy + '-' + mm + '-' + dd;
    dateInput.value = formattedToday;
});
const incomeData = {
    amount: document.getElementById('amount').value,
    description: document.getElementById('description').value,
    category: document.getElementById('category').value,
    date: document.getElementById('incomeDate').value 
};
const ctx = document.getElementById('incomeChart').getContext('2d');
new Chart(ctx, {
    type: 'bar',
    data: { },
    options: {
        responsive: true,
        maintainAspectRatio: true, 
        aspectRatio: 1.5,  
        scales: {
            y: {
                beginAtZero: true,
                ticks: { color: 'white', font: { size: 10 } } 
            },
            x: {
                ticks: { color: 'white' }
            }
        },
        plugins: {
            legend: { display: false }
        }
    }
});

const newExpense = {
    date: document.getElementById('date').value,
    desc: document.getElementById('desc').value,
    cat: document.getElementById('category').value, 
    amt: "-$" + document.getElementById('amount').value,
    type: 'ex' 
};

let transactions = JSON.parse(localStorage.getItem('myTransactions')) || [];
transactions.unshift(newExpense);
localStorage.setItem('myTransactions', JSON.stringify(transactions));


