    const blobUrlMap = {};

        function upload_toggleDropdown(id) {
            // Close all other dropdowns first
            ['poiDropdown', 'poaDropdown', 'porDropdown', 'dobDropdown'].forEach(dropId => {
                if(document.getElementById(dropId)) {
                    document.getElementById(dropId).classList.add('hidden');
                }
            });
            
            const dropdown = document.getElementById(id);
            if (dropdown) {
                dropdown.classList.toggle('hidden');
            }
        }

        function upload_selectOption(inputId, dropdownId, value) {
            document.getElementById(inputId).value = value;
            document.getElementById(dropdownId).classList.add('hidden');
        }

        function updateScore(scoreElementId) {
            const min = 70; 
            const max = 98; 
            const randomScore = Math.floor(Math.random() * (max - min + 1)) + min;
            
            const scoreContainer = document.getElementById(scoreElementId);
            const scoreValueElement = scoreContainer.querySelector('span:last-child');
            
            scoreContainer.classList.remove('hidden');
            scoreContainer.classList.add('flex');

            scoreValueElement.textContent = `${randomScore}/100`;

            // Reset classes
            scoreContainer.className = 'w-full max-w-[500px] p-2 border rounded-lg items-center justify-between text-xs flex';
            scoreValueElement.className = 'font-bold';
            
            if (randomScore < 70) {
                // Low Score (Red/Warning)
                scoreContainer.classList.add('bg-red-50', 'border-red-200');
                scoreValueElement.classList.add('text-red-700');
            } else if (randomScore < 90) {
                // Medium Score (Yellow/Satisfactory)
                scoreContainer.classList.add('bg-yellow-50', 'border-yellow-200');
                scoreValueElement.classList.add('text-yellow-700');
            } else {
                // High Score (Green/Excellent)
                scoreContainer.classList.add('bg-green-50', 'border-green-200');
                scoreValueElement.classList.add('text-green-700');
            }
        }

        // Opens the generated Blob URL in a new window/tab
        function viewBlob(url) {
            if (url) {
                window.open(url, '_blank');
            } else {
                alert('No document selected to view.');
            }
        }
        // Variables to hold uploaded files
let name_gender_proof = null;
let address_proof = null;
let porFile = null;
let dob_proof = null;

        // Handles file input change, generates Blob URL, and updates UI
        function upload_handleFileUpload(fileInputId, scoreElementId, displayElementId, browseLabelId, viewButtonId) {
            const fileInput = document.getElementById(fileInputId);
            const fileDisplay = document.getElementById(displayElementId);
            const browseLabel = document.getElementById(browseLabelId);
            const viewButton = document.getElementById(viewButtonId);
            const documentId = fileInputId.replace('File', ''); // e.g., 'poi'

            // Revoke old URL for memory cleanup
            if (blobUrlMap[documentId]) {
                URL.revokeObjectURL(blobUrlMap[documentId]);
                delete blobUrlMap[documentId];
            }

            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                 if (documentId === "poi") name_gender_proof = file;
        if (documentId === "poa") address_proof = file;
        if (documentId === "por") porFile = file;
        if (documentId === "dob") dob_proof= file;
                const fileName = file.name;

                // --- 1. CREATE BLOB URL ---
                const blobUrl = URL.createObjectURL(file);
                blobUrlMap[documentId] = blobUrl;
                viewButton.setAttribute('data-blob-url', blobUrl);

                // 2. Display filename
                fileDisplay.textContent = fileName;
                fileDisplay.classList.remove('hidden');
                fileDisplay.title = fileName; 

                // 3. Toggle buttons (Browse to View)
                browseLabel.classList.add('hidden');
                viewButton.classList.remove('hidden');
                
                // 4. Update the quality score
                updateScore(scoreElementId);

            } else {
                // Reset state if file selection is cancelled
                fileDisplay.classList.add('hidden');
                fileDisplay.textContent = '';
                browseLabel.classList.remove('hidden');
                viewButton.classList.add('hidden');
                viewButton.setAttribute('data-blob-url', '');
            }
        }
        // ----------------------------------------

        // Close dropdowns when clicking outside
        document.addEventListener('click', function(e) {
            const dropdowns = ['poiDropdown', 'poaDropdown', 'porDropdown', 'dobDropdown'];
            
            let clickedDropdownControl = false;
            dropdowns.forEach(id => {
                const dropdownMenu = document.getElementById(id);
                const relativeContainer = dropdownMenu ? dropdownMenu.closest('.relative') : null; 
                
                if (relativeContainer && relativeContainer.contains(e.target)) {
                    clickedDropdownControl = true; 
                }
            });
            
            if (!clickedDropdownControl) {
                dropdowns.forEach(id => {
                    const dropdownEl = document.getElementById(id);
                    if (dropdownEl && !dropdownEl.classList.contains('hidden')) {
                        dropdownEl.classList.add('hidden');
                    }
                });
            }
        });
function formatDateToYYYYMMDD(dateStr) {
  if (!dateStr) return "";

  // expected input: DD-MM-YYYY or DD/MM/YYYY
  const parts = dateStr.includes("-")
    ? dateStr.split("-")
    : dateStr.split("/");

  const [dd, mm, yyyy] = parts;
  return `${yyyy}-${mm.padStart(2, "0")}-${dd.padStart(2, "0")}`;
}

function submit_passport() {
  const data = new FormData();

  // -------- BASIC FIELDS --------
  const parts= document.querySelector('input[placeholder="Full Name"]').value
    const [first,last] = parts;

  data.append("first_name", first);
    data.append("last_name", last);

  data.append("gender", document.getElementById("genderInput").value);
  console.log(document.getElementById("genderInput").value)
  data.append("dob", formatDateToYYYYMMDD(document.getElementById("dobInput").value));

  data.append("phone", document.querySelector('input[type="tel"]').value);
  data.append("email", document.getElementById("email").value);

  // -------- ADDRESS --------
  data.append("present_address_line", document.querySelector('input[placeholder="Address"]').value);
  //data.append("region", document.getElementById("regionInput").value);
  data.append("present_city", document.getElementById("cityInput").value);
  data.append("zone", document.getElementById("zoneInput").value);
  data.append("present_state", document.getElementById("state").value);
  data.append("present_pincode", document.getElementById("pin").value);
 if (name_gender_proof) data.append("name_gender_proof",name_gender_proof );
    if (address_proof) data.append("address_proof", address_proof);
    if (dob_proof) data.append("dob_proof", dob_proof);
  // -------- FILE --------
  const fileInput = document.getElementById("fileInput");
  if (fileInput.files.length > 0) {
    data.append("document", fileInput.files[0]);
  }

  // -------- DEBUG --------
  for (let pair of data.entries()) {
    console.log(pair[0], pair[1]);
  }

  // -------- API CALL --------
 fetch("http://127.0.0.1:8000/api/passport/create/", {
  method: "POST",
  body: data   // FormData
})
.then(res => res.json())
.then(data => {
  console.log(data);
  alert("Passport Application Submitted Successfully");
})
.catch(err => {
  console.error(err);
});
}


function verify_passport() {
    const data = new FormData();

    // -------- BASIC FIELDS --------
    const parts = document.querySelector('input[placeholder="Full Name"]').value.split(" ");
    const first = parts[0] || "";
    const last = parts.slice(1).join(" ") || "";

    data.append("first_name", first);
    data.append("last_name", last);
    data.append("gender", document.getElementById("genderInput").value);
    data.append("dob", formatDateToYYYYMMDD(document.getElementById("dobInput").value));
    data.append("phone", document.querySelector('input[type="tel"]').value);
    data.append("email", document.getElementById("email").value);

    // -------- ADDRESS --------
    data.append("permanent_address_line", document.querySelector('input[placeholder="Address"]').value);
    data.append("permanent_city", document.getElementById("cityInput").value);
    data.append("permanent_country", document.getElementById("zoneInput").value);
    data.append("permanent_state", document.getElementById("state").value);
    data.append("permanent_pincode", document.getElementById("pin").value);
   //data.append("permanent_country", document.getElementById("pin").value);


    // -------- FILES --------
    if (name_gender_proof) data.append("name_gender_proof", name_gender_proof);
    if (address_proof) data.append("address_proof", address_proof);
    if (dob_proof) data.append("dob_proof", dob_proof);
    if (poiFile) data.append("poiFile", poiFile);
    if (poaFile) data.append("poaFile", poaFile);
    if (porFile) data.append("porFile", porFile);
    if (dobFile) data.append("dobFile", dobFile);

    // -------- DEBUG --------
    console.log("Verify Passport Data:");
    for (let pair of data.entries()) {
        console.log(pair[0], pair[1]);
    }

    // -------- OPTIONAL API CALL --------
    // If you have a verification endpoint, you can send this FormData
    fetch("http://127.0.0.1:8000/api/verify-documents/", {
        method: "POST",
        body: data
    })
    .then(res => res.json())
    .then(resp => {
        console.log("Verification Response:", resp);
        alert("Passport data verified successfully!");
    })
    .catch(err => {
        console.error("Verification Error:", err);
    });
}
