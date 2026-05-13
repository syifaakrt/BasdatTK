// =====================
// STATE
// =====================
let mitraData = [];
let editEmail = null;

// =====================
// HELPERS
// =====================
function getDurasi(tanggal) {
  const start = new Date(tanggal);
  const now = new Date();
  const diffDays = Math.floor((now - start) / (1000 * 60 * 60 * 24));
  const years = Math.floor(diffDays / 365);
  const months = Math.floor((diffDays % 365) / 30);
  if (years > 0) return `${years} thn ${months} bln`;
  return `${months} bulan`;
}

function getCsrfToken() {
  return document.cookie.split(';')
    .map(c => c.trim())
    .find(c => c.startsWith('csrftoken='))
    ?.split('=')[1] || '';
}

function populatePenyediaFilter() {
  const select = document.getElementById('filterPenyedia');
  const ids = [...new Set(mitraData.map(m => m.idPenyedia))].sort((a, b) => a - b);
  while (select.options.length > 1) select.remove(1);
  ids.forEach(id => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = `Penyedia #${id}`;
    select.appendChild(opt);
  });
}

// =====================
// MODAL HELPERS
// =====================
function showModal() {
  const m = document.getElementById('modalForm');
  m.classList.remove('hidden');
  m.classList.add('flex');
}

function closeModal() {
  const m = document.getElementById('modalForm');
  m.classList.add('hidden');
  m.classList.remove('flex');
}

document.getElementById('modalForm').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

// =====================
// RENDER TABLE
// =====================
function renderTable(data) {
  const source = data || mitraData;
  const tbody = document.getElementById('mitraTable');
  tbody.innerHTML = '';

  const uniquePenyedia = new Set(mitraData.map(m => m.idPenyedia)).size;
  const earliestYear = mitraData.length
    ? Math.min(...mitraData.map(m => new Date(m.tanggalKerjaSama).getFullYear()))
    : '-';

  document.getElementById('totalMitra').textContent       = mitraData.length;
  document.getElementById('mitraAktif').textContent       = mitraData.length;
  document.getElementById('totalPenyedia').textContent    = uniquePenyedia;
  document.getElementById('kerjasamaTerlama').textContent = earliestYear !== '-' ? earliestYear : '-';

  if (source.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-gray-400 py-6 text-sm">Tidak ada data ditemukan.</td></tr>`;
    return;
  }

  source.forEach((m) => {
    const durasi = getDurasi(m.tanggalKerjaSama);
    tbody.innerHTML += `
      <tr class="border-b border-gray-100 last:border-0 hover:bg-gray-50">
        <td class="px-3.5 py-2.5 text-sm font-semibold text-gray-500 font-mono">#${m.idPenyedia}</td>
        <td class="px-3.5 py-2.5 text-xs text-blue-500">${m.emailMitra}</td>
        <td class="px-3.5 py-2.5 text-sm font-medium text-[#1a2540]">${m.namaMitra}</td>
        <td class="px-3.5 py-2.5 text-xs text-gray-500">${m.tanggalKerjaSama}</td>
        <td class="px-3.5 py-2.5">
          <span class="text-[11px] font-medium px-2.5 py-1 rounded-full bg-blue-100 text-blue-800">${durasi}</span>
        </td>
        <td class="px-3.5 py-2.5">
          <div class="flex gap-1.5 items-center">
            <button onclick="openEdit('${m.emailMitra}')" title="Edit"
              class="text-blue-500 hover:bg-blue-50 text-base px-1.5 py-0.5 rounded transition">✎</button>
            <button onclick="deleteMitra('${m.emailMitra}', '${m.namaMitra}')" title="Hapus"
              class="text-red-500 hover:bg-red-50 text-base px-1.5 py-0.5 rounded transition">✕</button>
          </div>
        </td>
      </tr>
    `;
  });
}

// =====================
// FILTER
// =====================
function filterTable() {
  const search   = document.getElementById('searchInput').value.toLowerCase();
  const penyedia = document.getElementById('filterPenyedia').value;
  const filtered = mitraData.filter(m => {
    const matchSearch   = m.namaMitra.toLowerCase().includes(search) || m.emailMitra.toLowerCase().includes(search);
    const matchPenyedia = penyedia === '' || String(m.idPenyedia) === penyedia;
    return matchSearch && matchPenyedia;
  });
  renderTable(filtered);
}

// =====================
// FETCH DATA FROM API
// =====================
async function loadMitra() {
  try {
    const res = await fetch('/rewards/api/mitra/');
    const data = await res.json();
    if (res.ok) {
      mitraData = data;
      populatePenyediaFilter();
      filterTable();
    } else {
      alert('Gagal memuat data: ' + (data.error || 'Unknown error'));
    }
  } catch (e) {
    alert('Gagal konek ke server: ' + e.message);
  }
}

// =====================
// MODAL OPEN
// =====================
function openCreate() {
  editEmail = null;
  document.getElementById('modalTitle').textContent  = 'Tambah Mitra';
  document.getElementById('emailMitra').value        = '';
  document.getElementById('idPenyedia').value        = '';
  document.getElementById('namaMitra').value         = '';
  document.getElementById('tanggalKerjaSama').value  = '';
  // Enable email field for create
  document.getElementById('emailMitra').disabled = false;
  showModal();
}

function openEdit(email) {
  const m = mitraData.find(m => m.emailMitra === email);
  if (!m) return;
  editEmail = email;
  document.getElementById('modalTitle').textContent  = 'Edit Mitra';
  document.getElementById('emailMitra').value        = m.emailMitra;
  document.getElementById('idPenyedia').value        = m.idPenyedia;
  document.getElementById('namaMitra').value         = m.namaMitra;
  document.getElementById('tanggalKerjaSama').value  = m.tanggalKerjaSama;
  // Disable email field on edit (email is the PK)
  document.getElementById('emailMitra').disabled = true;
  showModal();
}

// =====================
// SAVE (Create / Update)
// =====================
async function saveMitra() {
  const emailMitra       = document.getElementById('emailMitra').value.trim();
  const idPenyedia       = document.getElementById('idPenyedia').value.trim();
  const namaMitra        = document.getElementById('namaMitra').value.trim();
  const tanggalKerjaSama = document.getElementById('tanggalKerjaSama').value;

  if (!emailMitra || !idPenyedia || !namaMitra || !tanggalKerjaSama) {
    alert('Harap lengkapi semua field!');
    return;
  }

  const payload = {
    emailMitra,
    idPenyedia: parseInt(idPenyedia),
    namaMitra,
    tanggalKerjaSama,
  };

  const url = editEmail
    ? `/rewards/api/mitra/update/${encodeURIComponent(editEmail)}/`
    : `/rewards/api/mitra/create/`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      closeModal();
      await loadMitra();
    } else {
      alert('Gagal menyimpan: ' + (data.error || 'Unknown error'));
    }
  } catch (e) {
    alert('Gagal konek ke server: ' + e.message);
  }
}

// =====================
// DELETE
// =====================
async function deleteMitra(email, nama) {
  if (!confirm(`Hapus mitra "${nama}"?`)) return;
  try {
    const res = await fetch(`/rewards/api/mitra/delete/${encodeURIComponent(email)}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() },
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await loadMitra();
    } else {
      alert('Gagal menghapus: ' + (data.error || 'Unknown error'));
    }
  } catch (e) {
    alert('Gagal konek ke server: ' + e.message);
  }
}

// =====================
// INIT
// =====================
loadMitra();