document.getElementById("autodate").innerText = new Date().toLocaleDateString();

const dashboard = document.querySelector(".dashboard-container");
const sidebarToggle = document.getElementById("sidebarToggle");
const closeNav = document.getElementById("closenav");

sidebarToggle.addEventListener("click", function () {
    dashboard.classList.add("sidebar-open");
});

closeNav.addEventListener("click", function () {
    dashboard.classList.remove("sidebar-open");
});

document.querySelectorAll('.toggle-form').forEach(form => {
    form.addEventListener('submit', event => {
        if (!confirm(`${form.dataset.action} this user?`)) {
            event.preventDefault();
        }
    });
});