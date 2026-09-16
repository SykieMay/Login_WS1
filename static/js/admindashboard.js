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