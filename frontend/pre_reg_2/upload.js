const blobUrlMap = {};

function upload_toggleDropdown(id) {
  // Close all other dropdowns first
  ['poiDropdown', 'poaDropdown', 'porDropdown', 'dobDropdown'].forEach(dropId => {
    if (document.getElementById(dropId)) {
      document.getElementById(dropId).classList.add('hidden');
    }
  });

  const dropdown = document.getElementById(id);
  if (dropdown) {
    dropdown.classList.toggle('hidden');
  }
}

// async function detectAadhar(file)
// {
//   const formData=new FormData();
//   formData.append('file',file)
//   const response=await fetch ('http://localhost:8000/api/aadhaar-detect/',{
//     method:'POST',
//     body:formData
//   });
//   if(!response.ok){
//     throw new Error('Aadhar detect api failed');
//   }
//   let ans=await response.json();
//   return ans.is_aadhar===true;
 
// }

async function detectAadhar(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/api/aadhaar-detect/', {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    throw new Error('Aadhaar detect API failed');
  }

  const data = await response.json();
  return data.is_aadhaar === true;
}


const selectedDocTypeMap = {}
function selectOption(inputId, dropdownId, value) {
  document.getElementById(inputId).value = value;
  document.getElementById(dropdownId).classList.add('hidden');

  const documentId = inputId.replace('Input', ''); // poi, poa, dob
  selectedDocTypeMap[documentId] = value;

  console.log('Selected type:', documentId, value);
}


async function updateScore(scoreElementId, file) {
  const scoreContainer = document.getElementById(scoreElementId);
  const scoreValueElement = scoreContainer.querySelector('span:last-child');

  // Loading state
  scoreContainer.classList.remove('hidden');
  scoreContainer.className =
    'w-full max-w-[500px] p-2 border rounded-lg flex items-center justify-between text-xs bg-gray-50 border-gray-200';
  scoreValueElement.className = 'font-bold text-gray-600';
  scoreValueElement.textContent = 'Checking...';

  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('http://localhost:8000/api/quality-score/', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error('API error');
    }

    const { final_quality_score } = await response.json();

    const score = Math.round(final_quality_score);

    // Reset styling
    scoreContainer.className =
      'w-full max-w-[500px] p-2 border rounded-lg flex items-center justify-between text-xs';
    scoreValueElement.className = 'font-bold';
    scoreValueElement.textContent = `${score}/100`;

    // Color logic (same as before)
    if (score < 70) {
      scoreContainer.classList.add('bg-red-50', 'border-red-200');
      scoreValueElement.classList.add('text-red-700');
    } else if (score < 90) {
      scoreContainer.classList.add('bg-yellow-50', 'border-yellow-200');
      scoreValueElement.classList.add('text-yellow-700');
    } else {
      scoreContainer.classList.add('bg-green-50', 'border-green-200');
      scoreValueElement.classList.add('text-green-700');
    }

  } catch (error) {
    console.error(error);
    scoreContainer.className =
      'w-full max-w-[500px] p-2 border rounded-lg flex items-center justify-between text-xs bg-red-50 border-red-200';
    scoreValueElement.className = 'font-bold text-red-700';
    scoreValueElement.textContent = 'Failed';
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
// async function upload_handleFileUpload(fileInputId, scoreElementId, displayElementId, browseLabelId, viewButtonId) {
//   const fileInput = document.getElementById(fileInputId);
//   const fileDisplay = document.getElementById(displayElementId);
//   const browseLabel = document.getElementById(browseLabelId);
//   const viewButton = document.getElementById(viewButtonId);
//   const documentId = fileInputId.replace('File', ''); // e.g., 'poi'

//   // Revoke old URL for memory cleanup
//   if (blobUrlMap[documentId]) {
//     URL.revokeObjectURL(blobUrlMap[documentId]);
//     delete blobUrlMap[documentId];
//   }

//   if (fileInput.files.length > 0) {
//     const file = fileInput.files[0];
//     const selectedType = selectedDocTypeMap[documentId];
//     if (documentId === "poi") name_gender_proof = file;
//     if (documentId === "poa") address_proof = file;
//     if (documentId === "dob") dob_proof = file;
//     const fileName = file.name;

//     // --- 1. CREATE BLOB URL ---
//     const blobUrl = URL.createObjectURL(file);
//     blobUrlMap[documentId] = blobUrl;
//     viewButton.setAttribute('data-blob-url', blobUrl);

//     // 2. Display filename
//     fileDisplay.textContent = fileName;
//     fileDisplay.classList.remove('hidden');
//     fileDisplay.title = fileName;

//     // 3. Toggle buttons (Browse to View)
//     browseLabel.classList.add('hidden');
//     viewButton.classList.remove('hidden');

//     // 4. Update the quality score
//     updateScore(scoreElementId,file);

//     if (!selectedType) {
//       alert('Please select a document type before uploading the file.');
//       fileInput.value = '';
//       return;
//     }

//     console.log("Checking if the document is aadhar or not",selectedType)

//     if(selectedType && selectedType.toLowerCase().includes('aadhar')){
//           console.log("Checking if the document is aadhar or not2")

//       try {
//         const result=await detectAadhar(file)
//         if (!result) {
//           alert('The uploaded document is not a valid Aadhaar card. Please upload a correct Aadhaar document.');
//         }
//         console.log("aadhar card:",result)
//       } catch (error) {
//         console.log("Error in calling api",error);
//       }
//     }

//   } else {
//     // Reset state if file selection is cancelled
//     fileDisplay.classList.add('hidden');
//     fileDisplay.textContent = '';
//     browseLabel.classList.remove('hidden');
//     viewButton.classList.add('hidden');
//     viewButton.setAttribute('data-blob-url', '');
//   }
// }

async function upload_handleFileUpload(
  fileInputId,
  scoreElementId,
  displayElementId,
  browseLabelId,
  viewButtonId
) {
  const fileInput = document.getElementById(fileInputId);
  const fileDisplay = document.getElementById(displayElementId);
  const browseLabel = document.getElementById(browseLabelId);
  const viewButton = document.getElementById(viewButtonId);
  const scoreContainer = document.getElementById(scoreElementId);
  const documentId = fileInputId.replace('File', ''); // poi / poa / dob

  // --- Cleanup previous blob ---
  if (blobUrlMap[documentId]) {
    URL.revokeObjectURL(blobUrlMap[documentId]);
    delete blobUrlMap[documentId];
  }

  if (fileInput.files.length === 0) {
    // Reset UI
    fileDisplay.classList.add('hidden');
    fileDisplay.textContent = '';
    browseLabel.classList.remove('hidden');
    viewButton.classList.add('hidden');
    viewButton.setAttribute('data-blob-url', '');
    scoreContainer.classList.add('hidden');
    return;
  }

  const file = fileInput.files[0];
  const selectedType = selectedDocTypeMap[documentId];

  // ❗ Document type must be selected first
  if (!selectedType) {
    alert('Please select a document type before uploading the file.');
    fileInput.value = '';
    scoreContainer.classList.add('hidden');
    return;
  }

  // Save file reference
  if (documentId === 'poi') name_gender_proof = file;
  if (documentId === 'poa') address_proof = file;
  if (documentId === 'dob') dob_proof = file;

  // --- Blob preview ---
  const blobUrl = URL.createObjectURL(file);
  blobUrlMap[documentId] = blobUrl;
  viewButton.setAttribute('data-blob-url', blobUrl);

  // --- UI updates ---
  fileDisplay.textContent = file.name;
  fileDisplay.classList.remove('hidden');
  fileDisplay.title = file.name;

  browseLabel.classList.add('hidden');
  viewButton.classList.remove('hidden');

  console.log('Checking document type:', selectedType);

  // ===== AADHAAR FLOW =====
  if (selectedType.toLowerCase().includes('aadhar')) {
    try {
      const isAadhaar = await detectAadhar(file);
      console.log('Aadhaar detected:', isAadhaar);

      if (!isAadhaar) {
        alert(
          'The uploaded document is not a valid Aadhaar card. Please upload a correct Aadhaar document.'
        );

        // ❌ Aadhaar invalid → NO quality score
        scoreContainer.classList.add('hidden');
        return;
      }

      // ✅ Aadhaar valid → now calculate quality score
      await updateScore(scoreElementId, file);

    } catch (error) {
      console.error('Aadhaar detection failed:', error);
      scoreContainer.classList.add('hidden');
      return;
    }
  }

  // ===== NON-AADHAAR FLOW =====
  else {
    await updateScore(scoreElementId, file);
  }
}

// ----------------------------------------

// Close dropdowns when clicking outside
document.addEventListener('click', function (e) {
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
  const parts = document.querySelector('input[placeholder="Full Name"]').value
  const [first, last] = parts;

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
  if (name_gender_proof) data.append("name_gender_proof", name_gender_proof);
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
    ctx.fillText(`${fields[key].confidence_score * 100}%`, (x2 + 10), (y1 + y2) / 2);
    ctx.fillText(key, x2 + 10, (y1 + y2) / 2 + 30);
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
  data.append("present_country", document.getElementById("regionInput").value);

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
      const r = resp.verification_result;

      // NAME + GENDER
      renderDocument(
        name_gender_proof,
        "img-name-gender",
        "canvas-name-gender",
        {
          first_name: {
            label: "FIRST NAME",
            ...r.first_name
          },
          gender: {
            label: "GENDER",
            ...r.gender
          },
          last_name: {
            label: "LAST NAME",
            ...r.last_name
          }
        }
      );

      // DOB
      renderDocument(
        dob_proof,
        "img-dob",
        "canvas-dob",
        {
          date_of_birth: {
            label: 'DOB',
            ...r.date_of_birth
          }
        }
      );

      // ADDRESS  //problem-sent to elhan
      renderDocument(
        address_proof,
        "img-address",
        "canvas-address",
        r.address
      );




      console.log("Verification Response:", resp);
      alert("Passport data verified successfully!");
    })
    .catch(err => {
      console.error("Verification Error:", err);
    });
}
function pickFields(result, keys) {
  const fields = {};
  keys.forEach(k => {
    if (result[k]?.coordinates) {
      fields[k] = result[k];
    }
  });
  return fields;
}


function renderDocument(file, imgId, canvasId, fields) {
  if (!file) return;

  const img = document.getElementById(imgId);
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext("2d");

  img.src = URL.createObjectURL(file);

  img.onload = () => {
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scaleX = canvas.width / img.naturalWidth;
    const scaleY = canvas.height / img.naturalHeight;

    Object.values(fields).forEach(field => {
      const [x1, y1, x2, y2] = field.coordinates;

      ctx.strokeStyle = "lime";
      ctx.lineWidth = 2;
      ctx.strokeRect(
        x1 * scaleX,
        y1 * scaleY,
        (x2 - x1) * scaleX,
        (y2 - y1) * scaleY
      );
      const rx = x1 * scaleX;
      const ry = y1 * scaleY;
      const rw = (x2 - x1) * scaleX;
      const rh = (y2 - y1) * scaleY;


      ctx.fillStyle = "lime";
      ctx.font = "16px Arial";

      const label = `${field.label || field.name || "FIELD"} ${Math.round(
        (field.match_score || 0) * 100
      )}%`;

      ctx.fillText(label, rx, ry - 5);

    });
    URL.revokeObjectURL(img.src);

  }
}
