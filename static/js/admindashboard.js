document.getElementById("autodate").innerText = new Date().toLocaleDateString();

function filterTeachers(select, programId) {
    if (!select) return;
    for (const option of select.options) {
        if (!option.value) {
            option.hidden = false;
            continue;
        }
        option.hidden = !programId || option.dataset.programId !== programId;
    }
    if (select.selectedOptions[0]?.hidden) select.value = "";
}

const subjectProgram = document.getElementById("subject-program");
const subjectTeacher = document.getElementById("subject-teacher");

if (subjectProgram && subjectTeacher) {
    const updateTeacherChoices = () => filterTeachers(subjectTeacher, subjectProgram.value);
    subjectProgram.addEventListener("change", updateTeacherChoices);
    updateTeacherChoices();
}

document.querySelectorAll(".subject-teacher-form").forEach(form => {
    filterTeachers(form.querySelector('select[name="teacher_id"]'), form.dataset.programId);
});

const sidebarToggle = document.getElementById("sidebarToggle");

function setSidebarOpen(isOpen) {
    document.body.classList.toggle("sidebar-open", isOpen);
    if (sidebarToggle) {
        sidebarToggle.setAttribute("aria-expanded", String(isOpen));
        const icon = sidebarToggle.querySelector("i");
        if (icon) {
            icon.classList.toggle("fa-bars", !isOpen);
            icon.classList.toggle("fa-times", isOpen);
        }
    }
}

if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function () {
        setSidebarOpen(!document.body.classList.contains("sidebar-open"));
    });
}

document.querySelectorAll("#sidebar-container .navbar a").forEach(link => {
    link.addEventListener("click", () => setSidebarOpen(false));
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape") setSidebarOpen(false);
});
