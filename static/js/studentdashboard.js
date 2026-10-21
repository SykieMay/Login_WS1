document.addEventListener("DOMContentLoaded", function () {
    // Display today's date
    const dateElement = document.getElementById("autodate");

    if (dateElement) {
        const today = new Date();

        dateElement.textContent = today.toLocaleDateString("en-PH", {
            year: "numeric",
            month: "long",
            day: "numeric"
        });

        dateElement.dateTime = [
            today.getFullYear(),
            String(today.getMonth() + 1).padStart(2, "0"),
            String(today.getDate()).padStart(2, "0")
        ].join("-");
    }

    // Toggle the mobile sidebar
    const sidebarToggle = document.getElementById("sidebarToggle");

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            const isOpen = document.body.classList.toggle("sidebar-open");

            sidebarToggle.setAttribute("aria-expanded", String(isOpen));

            const icon = sidebarToggle.querySelector("i");

            if (icon) {
                icon.classList.toggle("fa-bars", !isOpen);
                icon.classList.toggle("fa-times", isOpen);
            }
        });
    }

    // Highlight the selected sidebar section
    const navLinks = document.querySelectorAll(
        "#sidebar-container .navbar a[href^='#']"
    );

    navLinks.forEach(function (link) {
        link.addEventListener("click", function () {
            navLinks.forEach(function (item) {
                item.closest("li")?.classList.remove("active");
            });

            link.closest("li")?.classList.add("active");

            document.body.classList.remove("sidebar-open");

            if (sidebarToggle) {
                sidebarToggle.setAttribute("aria-expanded", "false");

                const icon = sidebarToggle.querySelector("i");

                if (icon) {
                    icon.classList.add("fa-bars");
                    icon.classList.remove("fa-times");
                }
            }
        });
    });
});