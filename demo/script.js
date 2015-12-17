function main() {
  // Local Kinto
  var server = "https://kinto.dev.mozaws.net/v1";
  // var server = "http://localhost:8888/v1";

  // Basic Authentication
  var headers = {Authorization: "Basic " + btoa("user:pass")};
  // Bucket id
  var bucket = "fennec-ota";

  // Reference to demo form.
  var form = document.forms.upload;
  form.onsubmit = submitFile;

  // When collection is chosen in combobox, refresh list of records.
  form.elements.category.addEventListener("change", refreshRecords);

  // When file is chosen in form, read its content
  // using HTML5 File API.
  var attachment = {file: null, binary: null};
  var reader = new FileReader();
  reader.addEventListener("load", function () {
    attachment.binary = reader.result;
    form.elements.submit.removeAttribute('disabled');
  });
  form.elements.attachment.addEventListener("change", function () {
    if(reader.readyState === FileReader.LOADING) {
      reader.abort();
    }
    var field = form.elements.attachment;
    attachment.file = field.files[0];
    reader.readAsBinaryString(attachment.file);
  });

  // On startup, create bucket/collections objects if necessary, and load list.
  createObjects()
    .then(refreshRecords);


  function submitFile(event) {
    // Build the form submission manually, using auth headers.
    // Send file as multipart and form fields as serialized JSON.
    event.preventDefault();

    // Collection id
    var collection = form.elements.category.value;
    // Record id
    var record = uuid4();

    // Build form data
    var formData = new FormData();
    // Multipart attachment
    formData.append('attachment', attachment.file, attachment.file.name);
    // Record attributes as JSON encoded
    var attributes = {
      type: form.elements.type.value
    };
    formData.append('data', JSON.stringify(attributes));

    // Post form using GlobalFetch API
    var url = `${server}/buckets/${bucket}/collections/${collection}/records/${record}/attachment`;
    fetch(url, {method: "POST", body: formData, headers: headers})
     .then(function (result) {
        if (result.status > 400) {
          throw new Error('Failed');
        }
     })
     .then(refreshRecords)
     .catch(function (error) {
       document.getElementById("error").textContent = error.toString();
     });
  }

  function refreshRecords() {
    // Current collection id.
    var collection = form.elements.category.value;
    // List all records.
    var url = `${server}/buckets/${bucket}/collections/${collection}/records`;
    fetch(url, {headers: headers})
     .then(function (response) {
       return response.json();
     })
     .then(function (result) {
       var tbody = document.querySelector("#records tbody");
       tbody.innerHTML = "";
       result.data.forEach(function(record) {
         tbody.appendChild(renderRecord(record));
       });
     });
  }

  function renderRecord(record) {
    var tpl = document.getElementById("record-tpl");
    var row = tpl.content.cloneNode(true);

    var link = row.querySelector(".location a");
    link.setAttribute("href", record.attachment.location);
    link.textContent = record.attachment.filename;

    row.querySelector(".type").textContent = record.type;
    row.querySelector(".mimetype").textContent = record.attachment.mimetype;
    row.querySelector(".size").textContent = record.attachment.size;
    row.querySelector(".hash").textContent = record.attachment.hash;
    return row;
  }

  // Prepare demo objects.
  // This demo posts records in the ``fennec-ota`` bucket. The target *collection*
  // can be chosen in the form from ``font``, ``locale`` and ``hyphenation`` values.
  function createObjects() {
    var creationOptions = {method: 'PUT', headers: Object.assign({}, headers, {'If-None-Match': '*'})};
    return fetch(`${server}/buckets/${bucket}`, creationOptions)
      .then(function (response) {
        var allCollections = ['font', 'locale', 'hyphenation'].map(function (collectionId) {
           return fetch(`${server}/buckets/${bucket}/collections/${collectionId}`, creationOptions);
        });
        return Promise.all(allCollections);
      });
  }
}


// Generate random uuid4
// Source: http://stackoverflow.com/a/2117523
function uuid4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = crypto.getRandomValues(new Uint8Array(1))[0]%16|0, v = c == 'x' ? r : (r&0x3|0x8);
    return v.toString(16);
  });
}


window.addEventListener("DOMContentLoaded", main);
