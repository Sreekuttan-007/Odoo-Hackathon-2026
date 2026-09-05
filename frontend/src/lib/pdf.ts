import api from '../services/api';

function extractFilename(contentDisposition: string | undefined, fallback: string): string {
  const match = contentDisposition?.match(/filename="?([^"]+)"?/);
  return match ? match[1] : fallback;
}

export async function openPayslipPdf(payslipId: number): Promise<void> {
  const res = await api.get(`/payroll/payslips/${payslipId}/pdf`, { responseType: 'blob' });
  const filename = extractFilename(res.headers['content-disposition'], `payslip-${payslipId}.pdf`);
  const blobUrl = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
}
