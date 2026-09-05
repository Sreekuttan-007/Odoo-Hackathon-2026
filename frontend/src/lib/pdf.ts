import api from '../services/api';

export async function openPayslipPdf(payslipId: number): Promise<void> {
  const res = await api.get(`/payroll/payslips/${payslipId}/pdf`, { responseType: 'blob' });
  const blobUrl = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
  window.open(blobUrl, '_blank');
  setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
}
