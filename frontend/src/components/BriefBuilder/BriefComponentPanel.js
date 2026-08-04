"use client";

import { Button, Checkbox, Collapse, Select } from "antd";
import { DownOutlined } from "@ant-design/icons";
import { useBrief } from "@/context/BriefContextProvider";
import { BRIEF_COMPONENTS, BRIEF_COMPONENT_KEYS } from "@/static/config";

const { Panel } = Collapse;

/**
 * "Priority score build-up selection" — the left panel (Figma 4159:191071,
 * populated at 4155:179809).
 *
 * Binds to the DRAFT selection, never to what the preview is rendering. Apply
 * promotes draft -> URL; until then ticking a box costs nothing (design doc
 * D-4), which is the whole reason the design has an Apply button.
 */
const BriefComponentPanel = () => {
  const {
    administrations,
    adminsLoaded,
    draft,
    setDraft,
    apply,
    clearAll,
    isDirty,
  } = useBrief();

  const selected = new Set(draft.components);

  const setComponents = (keys) =>
    // Store in catalogue order, so the URL is stable however the user ticked.
    setDraft((prev) => ({
      ...prev,
      components: BRIEF_COMPONENT_KEYS.filter((k) => keys.has(k)),
    }));

  const toggle = (key) => {
    const next = new Set(selected);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    setComponents(next);
  };

  const toggleGroup = (group, checked) => {
    const next = new Set(selected);
    group.data.forEach((c) => (checked ? next.add(c.key) : next.delete(c.key)));
    setComponents(next);
  };

  const allSelected = selected.size === BRIEF_COMPONENT_KEYS.length;

  // One toggle rather than two links: once everything is ticked, "Select all"
  // has nothing left to do, so it becomes the way to undo itself.
  //
  // Scoped to the components only — distinct from the footer's "Clear all",
  // which also resets the Inkhundla and the narrative. Hence the label here is
  // "Clear all" under the "2. Choose components" heading it belongs to.
  const toggleAll = () =>
    setComponents(allSelected ? new Set() : new Set(BRIEF_COMPONENT_KEYS));

  return (
    <div className="flex w-full flex-col border border-cardBorder bg-white lg:w-[420px] lg:shrink-0">
      {/* Table header — fixed 70px in the design, not padding-derived. */}
      <div className="flex h-[70px] shrink-0 items-center border-b border-cardBorder p-4">
        <h2 className="mb-0 text-[20px] font-bold leading-[30px] text-neutral-800">
          Priority score build-up selection
        </h2>
      </div>

      {/* Card Content: pt-20, and 32px between the intro block and the groups. */}
      <div className="flex flex-col gap-8 pt-5">
        <div className="flex flex-col gap-6 px-4">
          <p className="mb-0 text-base leading-6 text-[#606060]">
            Select an Inkhundla, choose which components to include, and
            download a customised one-page brief. Only TWG members can download
            briefs.
          </p>

          <div className="border-t border-cardBorder" />

          <div className="flex flex-col gap-2">
            <label
              htmlFor="brief-inkhundla"
              className="text-base leading-6 text-neutral-800"
            >
              1. Select Inkhundla
            </label>
            <Select
              id="brief-inkhundla"
              showSearch
              allowClear
              className="w-full"
              placeholder="Select inkhundla"
              optionFilterProp="label"
              loading={!adminsLoaded}
              // Held back until the options exist. antd renders an unmatched
              // value as the raw number, so an id off the URL would show as
              // "5926129" until the list arrived — and permanently if it is not
              // a real Inkhundla.
              value={adminsLoaded ? draft.inkhundla : undefined}
              // allowClear hands back undefined — normalise so "nothing
              // selected" is always null, as the empty-state gate expects.
              onChange={(id) =>
                setDraft((prev) => ({ ...prev, inkhundla: id ?? null }))
              }
              options={administrations
                .map((a) => ({ value: a.id, label: a.name }))
                .sort((a, b) => a.label.localeCompare(b.label))}
            />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-base leading-6 text-neutral-800">
              2. Choose components
            </span>
            <Button type="link" className="h-auto p-0" onClick={toggleAll}>
              {allSelected ? "Clear all" : "Select all"}
            </Button>
          </div>
        </div>

        <Collapse
          bordered={false}
          defaultActiveKey={BRIEF_COMPONENTS.map((g) => g.group)}
          expandIconPosition="end"
          expandIcon={({ isActive }) => (
            <DownOutlined rotate={isActive ? 180 : 0} />
          )}
          className="brief-groups"
        >
          {BRIEF_COMPONENTS.map((group) => {
            const picked = group.data.filter((c) => selected.has(c.key)).length;
            return (
              <Panel
                key={group.group}
                header={
                  <Checkbox
                    checked={picked === group.data.length}
                    indeterminate={picked > 0 && picked < group.data.length}
                    // The header is the Collapse's own toggle, so a click on
                    // the checkbox must not also open/close the panel.
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => toggleGroup(group, e.target.checked)}
                  >
                    <span className="text-base leading-6 text-[#333]">
                      {group.label}
                    </span>
                  </Checkbox>
                }
                extra={
                  picked > 0 ? (
                    <Button
                      type="link"
                      className="h-auto"
                      style={{ padding: 0 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleGroup(group, false);
                      }}
                    >
                      Clear
                    </Button>
                  ) : null
                }
              >
                <div className="flex flex-col gap-4">
                  {group.data.map((c) => (
                    <Checkbox
                      key={c.key}
                      checked={selected.has(c.key)}
                      onChange={() => toggle(c.key)}
                      // Alignment lives in .brief-groups (globals.css) — an
                      // `items-start` utility here loses to antd's runtime
                      // styles at equal specificity.
                      className="[&>span:last-child]:pl-2"
                    >
                      <span className="block text-base leading-6 text-[#333]">
                        {c.label}
                      </span>
                      <span className="block text-sm leading-[21px] text-[#606060]">
                        {c.description}
                      </span>
                    </Checkbox>
                  ))}
                </div>
              </Panel>
            );
          })}
        </Collapse>
      </div>

      <div className="mt-auto flex gap-2 border-t border-cardBorder p-4">
        <Button
          type="primary"
          className="h-11 flex-1"
          disabled={!isDirty}
          onClick={apply}
        >
          Apply
        </Button>
        <Button className="h-11 flex-1" onClick={clearAll}>
          Clear all
        </Button>
      </div>
    </div>
  );
};

export default BriefComponentPanel;
