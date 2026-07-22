function Field({ label, value }) {
  return (
    <div className="col-sm-6 mb-3">
      <dt className="small text-secondary">{label}</dt>
      <dd className="mb-0 text-break">{value === null || value === undefined ? 'Not available' : String(value)}</dd>
    </div>
  )
}

function BomItemCard({ item }) {
  const inventory = item.inventory
  const alternative = item.direct_alternative

  return (
    <article className="card h-100 border-0 shadow-sm">
      <div className="card-body p-4">
        <div className="d-flex align-items-start justify-content-between gap-2 mb-3">
          <div>
            <h2 className="h5 mb-1">{item.material_name}</h2>
            <span className="text-secondary small">Material #{item.material_id}</span>
          </div>
          <span className={`badge ${inventory.is_available ? 'text-bg-success' : 'text-bg-danger'}`}>
            {inventory.is_available ? 'Available' : 'Shortage'}
          </span>
        </div>

        <h3 className="h6 text-uppercase text-secondary">Material requirement</h3>
        <dl className="row mb-2">
          <Field label="Furniture material ID" value={item.furniture_material_id} />
          <Field label="Unit" value={item.unit} />
          <Field label="Base quantity" value={item.base_quantity} />
          <Field label="Wastage percentage" value={`${item.wastage_percentage}%`} />
          <Field label="Wastage quantity" value={item.wastage_quantity} />
          <Field label="Required quantity" value={item.required_quantity} />
          <Field label="Current unit price" value={item.current_unit_price} />
          <Field label="Line total" value={item.line_total} />
        </dl>

        <h3 className="h6 text-uppercase text-secondary border-top pt-3">Inventory</h3>
        <dl className="row mb-2">
          <Field label="Inventory ID" value={inventory.inventory_id} />
          <Field label="Quantity on hand" value={inventory.quantity_on_hand} />
          <Field label="Reorder level" value={inventory.reorder_level} />
          <Field label="Shortage quantity" value={inventory.shortage_quantity} />
          <Field label="Available" value={inventory.is_available ? 'Yes' : 'No'} />
        </dl>

        <h3 className="h6 text-uppercase text-secondary border-top pt-3">Direct alternative</h3>
        {alternative ? (
          <dl className="row mb-0">
            <Field label="Alternative material ID" value={alternative.alternative_material_id} />
            <Field label="Material name" value={alternative.alternative_material_name} />
            <Field label="Unit" value={alternative.alternative_unit} />
            <Field label="Current unit price" value={alternative.alternative_current_unit_price} />
            <Field label="Inventory ID" value={alternative.alternative_inventory_id} />
            <Field label="Quantity on hand" value={alternative.alternative_quantity_on_hand} />
            <Field label="Shortage quantity" value={alternative.alternative_shortage_quantity} />
            <Field label="Available" value={alternative.alternative_is_available ? 'Yes' : 'No'} />
            <Field label="Estimated line total" value={alternative.estimated_alternative_line_total} />
          </dl>
        ) : (
          <p className="text-secondary mb-0">No direct alternative configured.</p>
        )}
      </div>
    </article>
  )
}

export default BomItemCard
