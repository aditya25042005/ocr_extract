  function toggleDropdown(id) {
            const dropdown = document.getElementById(id);
            // Close other dropdowns
            const allDropdowns = [
                'genderDropdown', 
                'residenceDropdown', 
                'regionDropdown', 
                'provinceDropdown', 
                'cityDropdown', 
                'zoneDropdown',
                'datePickerDropdown'
            ];
            allDropdowns.forEach(d => {
                if(d !== id) document.getElementById(d)?.classList.add('hidden');
            });
            dropdown.classList.toggle('hidden');
        }

        function selectOption(inputId, dropdownId, value) {
            document.getElementById(inputId).value = value;
            document.getElementById(dropdownId).classList.add('hidden');
        }

        function filterDropdown(input, optionsContainerId) {
            const filter = input.value.toUpperCase();
            const container = document.getElementById(optionsContainerId);
            const divs = container.getElementsByTagName("div");
            for (let i = 0; i < divs.length; i++) {
                const txtValue = divs[i].textContent || divs[i].innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    divs[i].style.display = "";
                } else {
                    divs[i].style.display = "none";
                }
            }
        }

        // Close dropdowns when clicking outside
        document.addEventListener('click', function(e) {
            const dropdownIds = [
                'genderDropdown', 
                'residenceDropdown', 
                'regionDropdown', 
                'provinceDropdown', 
                'cityDropdown', 
                'zoneDropdown'
            ];
            
            // Check if click is strictly outside any of our custom dropdown structures
            // logic: if target is NOT inside a .relative container that holds a dropdown...
            
            // Simpler check: loop through all IDs. If one is open, check if click is inside its parent relative container.
            dropdownIds.forEach(id => {
                const dropdownEl = document.getElementById(id);
                if(dropdownEl && !dropdownEl.classList.contains('hidden')) {
                     // Get the parent card (the .relative z-XX container)
                     const wrapper = dropdownEl.closest('.relative.z-50') || 
                                     dropdownEl.closest('.relative.z-40') || 
                                     dropdownEl.closest('.relative.z-30') ||
                                     dropdownEl.closest('.relative.z-20'); 
                     
                     if (wrapper && !wrapper.contains(e.target)) {
                         dropdownEl.classList.add('hidden');
                     }
                }
            });
        });

        // --- Date Picker Logic (Existing) ---
        const monthNames = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
        let currentDate = new Date();
        let selectedDate = null;
        let currentMonth = currentDate.getMonth();
        let currentYear = currentDate.getFullYear();
        
        let viewMode = 'days';
        let yearRangeStart = currentYear - (currentYear % 24);

        function initDatePicker() {
            render();
            
            document.addEventListener('click', function(event) {
                const picker = document.getElementById('datePickerDropdown');
                const input = document.getElementById('dobInput');
                const btn = event.target.closest('button');
                const header = document.getElementById('currentMonthYear');
                
                if (!picker.contains(event.target) && 
                    event.target !== input && 
                    event.target !== header &&
                    (!btn || !btn.contains(document.querySelector('.fa-calendar-alt')))) {
                    picker.classList.add('hidden');
                    viewMode = 'days';
                }
            });
        }

        function toggleDatePicker(e) {
            if(e) e.stopPropagation();
            const picker = document.getElementById('datePickerDropdown');
            // Close others
            const allDropdowns = [
                'genderDropdown', 
                'residenceDropdown', 
                'regionDropdown', 
                'provinceDropdown', 
                'cityDropdown', 
                'zoneDropdown'
            ];
            allDropdowns.forEach(d => document.getElementById(d).classList.add('hidden'));
            
            picker.classList.toggle('hidden');
            if (!picker.classList.contains('hidden')) {
                viewMode = 'days';
                render();
            }
        }

        function openDatePicker() {
             // Close others
            const allDropdowns = [
                'genderDropdown', 
                'residenceDropdown', 
                'regionDropdown', 
                'provinceDropdown', 
                'cityDropdown', 
                'zoneDropdown'
            ];
            allDropdowns.forEach(d => document.getElementById(d).classList.add('hidden'));

            const picker = document.getElementById('datePickerDropdown');
            picker.classList.remove('hidden');
            viewMode = 'days';
            render();
        }

        // --- Navigation Handlers ---

        function handlePrev() {
            if (viewMode === 'days') {
                changeMonth(-1);
            } else {
                changeYearPage(-1);
            }
        }

        function handleNext() {
            if (viewMode === 'days') {
                changeMonth(1);
            } else {
                changeYearPage(1);
            }
        }

        function toggleViewMode() {
            viewMode = viewMode === 'days' ? 'years' : 'days';
            if (viewMode === 'years') {
                yearRangeStart = currentYear - (currentYear % 24);
            }
            render();
        }

        // --- Logic ---

        function changeMonth(step) {
            currentMonth += step;
            if (currentMonth > 11) {
                currentMonth = 0;
                currentYear++;
            } else if (currentMonth < 0) {
                currentMonth = 11;
                currentYear--;
            }
            render();
        }

        function changeYearPage(step) {
            yearRangeStart += (step * 24);
            render();
        }

        function render() {
            const daysView = document.getElementById('daysView');
            const yearsView = document.getElementById('yearsView');
            const headerLabel = document.getElementById('currentMonthYear');
            const caret = document.getElementById('headerCaret');

            if (viewMode === 'days') {
                daysView.classList.remove('hidden');
                yearsView.classList.add('hidden');
                headerLabel.innerText = `${monthNames[currentMonth]} ${currentYear}`;
                caret.classList.remove('rotate-180');
                renderCalendarDays();
            } else {
                daysView.classList.add('hidden');
                yearsView.classList.remove('hidden');
                const endYear = yearRangeStart + 23;
                headerLabel.innerText = `${yearRangeStart} – ${endYear}`;
                caret.classList.add('rotate-180');
                renderYearsGrid();
            }
        }

        function renderCalendarDays() {
            const grid = document.getElementById('calendarGrid');
            grid.innerHTML = '';

            const firstDay = new Date(currentYear, currentMonth, 1).getDay();
            const startOffset = firstDay === 0 ? 6 : firstDay - 1; 
            const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

            for (let i = 0; i < startOffset; i++) {
                grid.appendChild(document.createElement('div'));
            }

            for (let d = 1; d <= daysInMonth; d++) {
                const cell = document.createElement('div');
                cell.innerText = d;
                cell.className = "h-8 w-8 flex items-center justify-center rounded-full cursor-pointer hover:bg-gray-100 transition text-gray-700 text-sm";
                
                if (selectedDate && 
                    selectedDate.getDate() === d && 
                    selectedDate.getMonth() === currentMonth && 
                    selectedDate.getFullYear() === currentYear) {
                    cell.classList.add('bg-indigo-600', 'text-white', 'hover:bg-indigo-700', 'shadow-md');
                    cell.classList.remove('text-gray-700', 'hover:bg-gray-100');
                } else if (d === new Date().getDate() && currentMonth === new Date().getMonth() && currentYear === new Date().getFullYear() && !selectedDate) {
                    cell.classList.add('font-bold', 'text-indigo-600');
                }

                cell.onclick = () => selectDate(d, currentMonth, currentYear);
                grid.appendChild(cell);
            }
        }

        function renderYearsGrid() {
            const grid = document.getElementById('yearsGrid');
            grid.innerHTML = '';
            
            for (let i = 0; i < 24; i++) {
                const year = yearRangeStart + i;
                const cell = document.createElement('div');
                cell.innerText = year;
                cell.className = "py-2 px-1 rounded-full cursor-pointer hover:bg-gray-100 transition text-gray-700 font-medium";
                
                if (year === currentYear) {
                     cell.classList.add('bg-indigo-600', 'text-white', 'hover:bg-indigo-700', 'shadow-md');
                     cell.classList.remove('text-gray-700', 'hover:bg-gray-100');
                } else if (year === new Date().getFullYear()) {
                     cell.classList.add('text-indigo-600', 'font-bold');
                }

                cell.onclick = () => selectYear(year);
                grid.appendChild(cell);
            }
        }

        function selectDate(day, month, year) {
            selectedDate = new Date(year, month, day);
            const formattedDate = `${day}/${month + 1}/${year}`;
            document.getElementById('dobInput').value = formattedDate;
            document.getElementById('datePickerDropdown').classList.add('hidden');
            
            const today = new Date();
            let age = today.getFullYear() - year;
            const m = today.getMonth() - month;
            if (m < 0 || (m === 0 && today.getDate() < day)) {
                age--;
            }
            document.getElementById('ageInput').value = age;
            
            render();
        }

        function selectYear(year) {
            currentYear = year;
            viewMode = 'days';
            render();
        }

        function calculateDobFromAge() {
            const age = parseInt(document.getElementById('ageInput').value);
            if (!isNaN(age)) {
                const today = new Date();
                const year = today.getFullYear() - age;
                currentYear = year;
                if (!document.getElementById('datePickerDropdown').classList.contains('hidden')) {
                    render();
                }
            }
        }

        // Initialize on load
        window.addEventListener('DOMContentLoaded', initDatePicker);

        function validateAndContinue() {
            const btn = document.querySelector('button[onclick="validateAndContinue()"]');
            const originalText = btn.innerText;
            btn.innerText = "PROCESSING...";
            setTimeout(() => {
                btn.innerText = originalText;
                alert("Form Submitted! Proceeding to next step...");
            }, 800);
        }

 async function auto_fill() {
    const fileInput = document.getElementById("fileInput");
    const docType = document.getElementById("docType").value;

    const file = fileInput.files[0];

    if (!file || !docType) {
      alert("Please select a file and document type");
      return;
    }

    console.log("Uploaded File:", file);
    console.log("Document Type:", docType);

    // optional: file details
    console.log("File Name:", file.name);
    console.log("File Size:", file.size);
    console.log("File Type:", file.type);
 // Create FormData
  const formData = new FormData();
  formData.append("file", file);        // file field
  formData.append("type", docType);     // handwritten / printed

  try {
    const response = await fetch("http://127.0.0.1:8000/api/handwritten/ocr/", {
      method: "POST",
      body: formData
    });


    if (!response.ok) {
      throw new Error("Upload failed");
    }


    const data = await response.json();
    console.log("OCR Response:", data);

    /* ---------- AUTO FILL FROM fields ---------- */
    const fields = data.fields || {};

    // Full Name
    const fullName =
      `${fields["First Name"]?.value || ""} ` +
      `${fields["Middle Name"]?.value || ""} ` +
      `${fields["Last Name"]?.value || ""}`.trim();

    document.querySelector('input[placeholder="Full Name"]').value = fullName;

    // Phone
    if (fields["Phone"]) {
      document.querySelector('input[type="tel"]').value =
        fields["Phone"].value;
    }
    //gender
     if (fields["Gender"]) {
      document.querySelector('#genderInput').value =
        fields["Gender"].value;
        
    }

    // Address
    if (fields["Address"]) {
      document.querySelector('input[placeholder="Address"]').value =
        fields["Address"].value;
    }


///

 // City (custom dropdown input)
    if (fields["City"]) {
      document.getElementById("cityInput").value =
        fields["City"].value;
    }

    // Province / State
    if (fields["State"]) {
      document.querySelector('#state').value =
        fields["State"].value;
    }
    //DOB
     if (fields["DOB"]) {
      document.querySelector('#dobInput').value =
        fields["DOB"].value;
    }
//email
  if (fields["DOB"]) {
      document.querySelector('#dobInput').value =
        fields["DOB"].value;
    }
    //pincode
      if (fields["Pincode"]) {
      document.querySelector('#pin').value =
        fields["Pincode"].value;
    }

    // Country (if you later add field)
    if (fields["Country"]) {
      console.log("Country:", fields["Country"].value);
    }
  const img = new Image();

  // Open image
  img.src = URL.createObjectURL(file);

      // 4️⃣ Draw rectangles after image loads
    img.onload = () => {
      drawBoundingBoxes(img, data.fields);
    };

  } catch (error) {
    console.error("Error:", error);
  }
}


  
function drawBoundingBoxes(image, fields) {
  const canvas = document.getElementById("overlayCanvas");
  const ctx = canvas.getContext("2d");


  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0);

  Object.entries(fields).forEach(([key, field]) => {
    if (!field.coordinates) return;

    const [x1, x2, y1, y2] = field.coordinates;

    const x = Math.min(x1, x2);
    const y = Math.min(y1, y2);
    const w = Math.abs(x2 - x1);
    const h = Math.abs(y2 - y1);

    // Color based on confidence
    ctx.strokeStyle =
      field.confidence_score > 0.9 ? "green" :
      field.confidence_score > 0.7 ? "orange" : "red";

    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);

    ctx.fillStyle = ctx.strokeStyle;
    ctx.font = "30px Arial";
  //  ctx.fillText(key, x, y - 5);
       ctx.fillText(`${fields[key].confidence_score*100}%` ,(x2+10) , (y1+y2)/2);
          ctx.fillText(key ,x2+10 ,(y1+y2)/2+30);
  });
}

document.getElementById("fileInput").addEventListener("change", onFileSelect);

function onFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  loadImageToCanvas(file);
}

function loadImageToCanvas(file) {
  const canvas = document.getElementById("overlayCanvas");
  const ctx = canvas.getContext("2d");

  const img = new Image();
  img.src = URL.createObjectURL(file);

  img.onload = () => {
    // 🔹 Set actual canvas resolution
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;

    // 🔹 Draw image into canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    // 🔹 If you have OCR boxes
    // drawBoundingBoxes(img, data.fields);
  };
}


/////////
let currentPage = 0;

function nextPage() {
  currentPage = 1;
  document.getElementById("container").style.transform =
    "translateX(-100vw)";
  history.pushState({ page: 1 }, "", "#upload");
}

function prevPage() {
  currentPage = 0;
  document.getElementById("container").style.transform =
    "translateX(0vw)";
  history.pushState({ page: 0 }, "", "#demographic");
}
// Handle browser back button
window.onpopstate = function (event) {
  if (event.state?.page === 1) nextPage();
  else prevPage();
};
