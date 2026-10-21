document.getElementById("autodate").innerText = new Date().toLocaleDateString();

const sidebarToggle = document.getElementById("sidebarToggle");
const dashboardContainer = document.querySelector(".dashboard-container");

sidebarToggle.addEventListener("click", function () {
    dashboardContainer.classList.toggle("sidebar-hidden");
});

const close = document.getElementById("close");
const navbar = document.querySelector(".sidebar-container");

close.addEventListener("click", function () {
    navbar.classList.toggle("sidebar-container;")
});