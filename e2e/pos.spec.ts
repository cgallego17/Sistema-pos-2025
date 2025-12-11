import { test, expect } from '@playwright/test';

// Variables de prueba
const USERNAME = process.env.E2E_USER || 'admin';
const PIN = process.env.E2E_PIN || '1234';

test.describe('POS - Flujo básico desde el front', () => {
  test('login, apertura de caja, venta rápida y verificación de ticket', async ({ page }) => {
    // Login por PIN
    await page.goto('/');
    await page.fill('input[name="username"]', USERNAME);
    await page.fill('input[name="pin"]', PIN);
    await page.click('button[type="submit"]');

    // Abrir caja si muestra el modal
    const abrirCajaBtn = page.locator('button', { hasText: /abrir caja/i });
    if (await abrirCajaBtn.isVisible().catch(() => false)) {
      await page.fill('input[name="monto_inicial"]', '100000');
      await abrirCajaBtn.click();
      await expect(page.getByText(/caja abierta/i)).toBeVisible({ timeout: 10_000 });
    }

    // Ir a productos y agregar el primero al carrito
    await page.goto('/vender/');
    const primerProducto = page.locator('.product-card').first();
    await expect(primerProducto).toBeVisible();
    await primerProducto.click();

    // Ver carrito y procesar venta (efectivo)
    await page.click('button', { hasText: /procesar venta/i });
    await page.fill('input[name="monto_recibido"]', '200000');
    await page.click('button', { hasText: /confirmar/i });

    // Confirmación de venta
    await expect(page.getByText(/venta #/i)).toBeVisible({ timeout: 10_000 });

    // Ver detalle/ticket
    await page.click('a', { hasText: /ver ticket/i }).catch(() => {});
    await expect(page.getByText(/total/i)).toBeVisible();
  });
});


