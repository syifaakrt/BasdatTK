// =====================
// STATE
// =====================
let hadiahData = [];
let editKode = null;

// =====================
// HELPERS
// =====================
function getStatus(akhir) {
  return new Date(akhir) >= new Date() ? 'Aktif' : 'Expired';
}

function formatMiles(n) {
  return Number(n).toLocaleString('id-ID');
}

function getCsrfToken() {
  return document.cookie.split(';')
    .map(c => c.trim())
    .find(c => c.startsWith('csrftoken='))
    ?.split('=')[1] || '';
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
  const source = data || hadiahData;
  const tbody = document.getElementById('hadiahTable');
  tbody.innerHTML = '';

  let aktif = 0, expired = 0, totalMiles = 0;
  hadiahData.forEach(h => {
    const s = getStatus(h.akhir);
    if (s === 'Aktif') aktif++; else expired++;
    totalMiles += Number(h.miles);
  });

  document.getElementById('totalHadiah').textContent   = hadiahData.length;
  document.getElementById('hadiahAktif').textContent   = aktif;
  document.getElementById('hadiahExpired').textContent = expired;
  document.getElementById('totalMiles').textContent    = formatMiles(totalMiles);

  if (source.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-gray-400 py-6 text-sm">Tidak ada data ditemukan.</td></tr>`;
    return;
  }

  source.forEach((h) => {
    const status = getStatus(h.akhir);
    const badgeClass = status === 'Aktif' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
    tbody.innerHTML += `
      <tr class="border-b border-gray-100 last:border-0 hover:bg-gray-50">
        <td class="px-3.5 py-2.5 text-xs text-gray-400">${h.kode}</td>
        <td class="px-3.5 py-2.5">
          <div class="text-sm font-medium text-[#1a2540]">${h.nama}</div>
          <div class="text-[11px] text-gray-400 mt-0.5">${h.deskripsi}</div>
        </td>
        <td class="px-3.5 py-2.5 text-sm font-semibold text-[#1a2540]">${formatMiles(h.miles)}</td>
        <td class="px-3.5 py-2.5 text-xs text-gray-500">${h.mulai}</td>
        <td class="px-3.5 py-2.5 text-xs text-gray-500">${h.akhir}</td>
        <td class="px-3.5 py-2.5">
          <span class="text-[11px] font-medium px-2.5 py-1 rounded-full ${badgeClass}">${status}</span>
        </td>
        <td class="px-3.5 py-2.5">
          <div class="flex gap-1.5 items-center">
            <button onclick="openEdit('${h.kode}')" title="Edit"
              class="text-blue-500 hover:bg-blue-50 text-base px-1.5 py-0.5 rounded transition">✎</button>
            <button onclick="deleteHadiah('${h.kode}', '${h.nama}')" title="Hapus"
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
  const search = document.getElementById('searchInput').value.toLowerCase();
  const status = document.getElementById('filterStatus').value;
  const filtered = hadiahData.filter(h => {
    const matchSearch = h.nama.toLowerCase().includes(search) || h.deskripsi.toLowerCase().includes(search);
    const matchStatus = status === '' || getStatus(h.akhir) === status;
    return matchSearch && matchStatus;
  });
  renderTable(filtered);
}

// =====================
// FETCH DATA FROM API
// =====================
async function loadHadiah() {
  try {
    const res = await fetch('/rewards/api/hadiah/');
    const data = await res.json();
    if (res.ok) {
      hadiahData = data;
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
  editKode = null;
  document.getElementById('modalTitle').textContent = 'Tambah Hadiah';
  document.getElementById('nama').value = '';
  document.getElementById('miles').value = '';
  document.getElementById('deskripsi').value = '';
  document.getElementById('mulai').value = '';
  document.getElementById('akhir').value = '';
  showModal();
}

function openEdit(kode) {
  const h = hadiahData.find(h => h.kode === kode);
  if (!h) return;
  editKode = kode;
  document.getElementById('modalTitle').textContent = 'Edit Hadiah';
  document.getElementById('nama').value = h.nama;
  document.getElementById('miles').value = h.miles;
  document.getElementById('deskripsi').value = h.deskripsi;
  document.getElementById('mulai').value = h.mulai;
  document.getElementById('akhir').value = h.akhir;
  showModal();
}

// =====================
// SAVE (Create / Update)
// =====================
async function saveHadiah() {
  const nama      = document.getElementById('nama').value.trim();
  const miles     = document.getElementById('miles').value.trim();
  const deskripsi = document.getElementById('deskripsi').value.trim();
  const mulai     = document.getElementById('mulai').value;
  const akhir     = document.getElementById('akhir').value;

  if (!nama || !miles || !deskripsi || !mulai || !akhir) {
    alert('Harap lengkapi semua field!');
    return;
  }

  const idPenyedia = document.getElementById('idPenyedia').value.trim();
  if (!nama || !miles || !deskripsi || !mulai || !akhir || !idPenyedia) {
    alert('Harap lengkapi semua field!');
    return;
   }
  const payload = { nama, miles: parseInt(miles), deskripsi, mulai, akhir, idPenyedia: parseInt(idPenyedia) };
  const url = editKode
    ? `/rewards/api/hadiah/update/${editKode}/`
    : `/rewards/api/hadiah/create/`;

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
      await loadHadiah();
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
async function deleteHadiah(kode, nama) {
  if (!confirm(`Hapus hadiah "${nama}"?`)) return;
  try {
    const res = await fetch(`/rewards/api/hadiah/delete/${kode}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() },
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await loadHadiah();
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
loadHadiah();