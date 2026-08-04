"use client";

import { MinusCircleIcon, PlusCircleIcon } from "@/components/Icons";
import { PageHeader } from "@/components";
import { api } from "@/lib";
import {
  Badge,
  Button,
  DatePicker,
  Divider,
  Form,
  Input,
  InputNumber,
  message,
  Select,
  Skeleton,
  Table,
  Typography,
} from "antd";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import advancedUTC from "dayjs/plugin/utc";
import { DEFAULT_CDI_WEIGHTS, RUNDECK_JOB_STATUS_COLOR } from "@/static/config";

dayjs.extend(advancedFormat);
dayjs.extend(advancedUTC);

const { Title, Text } = Typography;
const { useForm } = Form;

const EmailListForm = ({ label, name }) => (
  <Form.List
    name={name}
    rules={[
      {
        validator: async (_, names) => {
          if (!names || names.length < 1) {
            return Promise.reject(new Error("At least 1 emails"));
          }
        },
      },
    ]}
  >
    {(fields, { add, remove }, { errors }) => (
      <div className="w-full mb-4">
        <div className="flex items-center justify-between mb-2">
          <Text strong>{label}</Text>
          <Button
            type="link"
            size="small"
            onClick={() => add()}
            icon={<PlusCircleIcon />}
            className="text-xs"
          >
            Add new
          </Button>
        </div>
        {fields.map(({ key, ...field }) => (
          <div key={key} className="flex items-center gap-2 mb-2">
            <Form.Item
              {...field}
              validateTrigger={["onChange", "onBlur"]}
              rules={[
                {
                  required: true,
                  whitespace: true,
                  type: "email",
                  message: "This is not a valid email",
                },
              ]}
              className="flex-1 !mb-0"
            >
              <Input placeholder="Email" type="email" />
            </Form.Item>
            {fields.length > 0 && (
              <a
                role="button"
                onClick={(e) => {
                  e.preventDefault();
                  remove(field.name);
                }}
              >
                <MinusCircleIcon />
              </a>
            )}
          </div>
        ))}
        <Form.Item className="!mb-0">
          <Form.ErrorList errors={errors} />
        </Form.Item>
      </div>
    )}
  </Form.List>
);

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    on_success_emails: [null],
    on_failure_emails: [null],
    on_exceeded_emails: [null],
    lst_weight: DEFAULT_CDI_WEIGHTS.lst,
    ndvi_weight: DEFAULT_CDI_WEIGHTS.ndvi,
    spi_weight: DEFAULT_CDI_WEIGHTS.spi,
    sm_weight: DEFAULT_CDI_WEIGHTS.sm,
  });
  const [loading, setLoading] = useState(false);
  const [admins, setAdmins] = useState([]);
  const [projects, setProjects] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [execList, setExecList] = useState([]);
  const [fetching, setFetching] = useState(true);
  const [preload, setPreload] = useState(true);
  const [newSetup, setNewSetup] = useState(false);
  const [jobChecking, setJobChecking] = useState(false);
  const [jobFetching, setJobFetching] = useState(false);
  const [jobExecuting, setJobExecuting] = useState(false);
  const [submittable, setSubmittable] = useState(false);
  const [form] = useForm();
  const router = useRouter();

  const tableProps = useMemo(() => {
    if (execList?.length <= 20) {
      return { loading: jobFetching, pagination: false };
    }
    return { loading: jobFetching };
  }, [execList, jobFetching]);

  const runJobNowIsDisabled = useMemo(() => {
    const totalSuccessEmails = settings?.on_success_emails?.length || 0;
    const totalFailureEmails = settings?.on_failure_emails?.length || 0;
    const totalExceededEmails = settings?.on_exceeded_emails?.length || 0;
    const totalEmails =
      totalSuccessEmails + totalFailureEmails + totalExceededEmails;
    const anyJobRunning = execList?.some((e) => e.status === "running");

    return totalEmails < 3 ||
      !submittable ||
      anyJobRunning ||
      (submittable && totalEmails < 3)
      ? true
      : false;
  }, [execList, settings, submittable]);

  const onFinish = async (payload) => {
    if (!settings.id) {
      message.error("Something went wrong. Please try again.");
      setPreload(true);
      return;
    }
    setLoading(true);
    try {
      const { message: resMessage, ...apiData } = await api(
        "PUT",
        `/admin/setting/${settings.id}`,
        payload,
      );
      if (resMessage) {
        message.warning(resMessage);
      } else {
        setSettings(apiData);
        message.success("Settings updated successfully.");
      }
      setLoading(false);
      router.refresh();
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const onFinishSetup = async (payload) => {
    setLoading(true);
    try {
      const apiData = await api("POST", "/admin/settings", payload);
      if (apiData?.id) {
        setNewSetup(false);
        setSettings(apiData);
      }
      setLoading(false);
      router.refresh();
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const onSelectProject = async (p) => {
    try {
      const _jobs = await api("GET", `/rundeck/project/${p}/jobs`);
      if (_jobs?.length) {
        setJobs(_jobs.map(({ name: label, id: value }) => ({ value, label })));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const onRunJob = async ({ year_month }) => {
    setJobExecuting(true);
    try {
      await api("POST", `/rundeck/job/${settings?.job_id}/execs`, {
        year_month: dayjs(year_month).format("YYYY-MM"),
        lst_weight: settings?.lst_weight,
        ndvi_weight: settings?.ndvi_weight,
        spi_weight: settings?.spi_weight,
        sm_weight: settings?.sm_weight,
      });

      setPreload(true);
      router.refresh();
      setJobExecuting(false);
    } catch (err) {
      setJobExecuting(false);
      console.error(err);
    }
  };

  const fetchData = useCallback(async () => {
    try {
      if (preload) {
        setPreload(false);
        const _projects = await api("GET", "/rundeck/projects");
        if (_projects?.length) {
          setProjects(
            _projects.map(({ label, name: value }) => ({ value, label })),
          );
        }
        const { contacts: _admins } = await api("GET", "/admin/contacts");
        setAdmins(_admins?.map((a) => ({ label: a, value: a })));

        const { results: _settings } = await api("GET", "/admin/settings");
        if (_settings?.length === 0) {
          setNewSetup(true);
        } else {
          setSettings({
            ...settings,
            ..._settings[0],
          });
          const { data: _execList } = await api(
            "GET",
            `/rundeck/job/${_settings[0]?.job_id}/execs`,
          );
          if (_execList?.length) {
            setExecList(_execList);
          }
        }
        setFetching(false);
      }
    } catch (err) {
      console.error(err);
      setPreload(false);
      setFetching(false);
    }
  }, [preload, settings]);

  const fetchExecutions = useCallback(async () => {
    try {
      if (jobChecking) {
        setJobFetching(true);
        setJobChecking(false);
        const { data: _execList } = await api(
          "GET",
          `/rundeck/job/${settings?.job_id}/execs`,
        );
        if (_execList?.length) {
          setExecList(_execList);
        }
        setJobFetching(false);
      }
    } catch (err) {
      console.error(err);
    }
  }, [settings, jobChecking]);

  const handleRunningJob = useCallback(() => {
    const runningJob = execList?.find((e) => e.status === "running");
    if (!preload && runningJob) {
      setTimeout(() => {
        setJobChecking(true);
      }, 10000); // 10 seconds
    }
  }, [execList, preload]);

  useEffect(() => {
    handleRunningJob();
  }, [handleRunningJob]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const settingsValues = Form.useWatch([], form);
  useEffect(() => {
    form
      .validateFields({
        validateOnly: true,
      })
      .then(() => setSubmittable(true))
      .catch(() => setSubmittable(false));
  }, [form, settingsValues]);

  return (
    <div className="w-full h-auto">
      <PageHeader
        title="Automation Settings"
        description="Manage email notifications, CDI weights, and Rundeck job executions."
      />

      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px]">
          <Skeleton loading={fetching} title paragraph>
            {newSetup ? (
              <section className="border border-cardBorder bg-white p-6">
                <Title level={3}>Rundeck Integration Setup</Title>
                <Form form={form} onFinish={onFinishSetup} layout="vertical">
                  <Form.Item
                    label="Project"
                    name="project_name"
                    rules={[{ required: true }]}
                  >
                    <Select
                      placeholder="Select Project"
                      onSelect={onSelectProject}
                      options={projects}
                    />
                  </Form.Item>
                  <Form.Item
                    label="Job"
                    name="job_id"
                    rules={[{ required: true }]}
                  >
                    <Select placeholder="Select Job" options={jobs} />
                  </Form.Item>
                  <Button
                    htmlType="submit"
                    disabled={!submittable}
                    loading={loading}
                  >
                    Submit
                  </Button>
                </Form>
              </section>
            ) : (
              <div className="w-full h-auto flex flex-col lg:flex-row gap-4">
                {/* Left column — Email & CDI Weight */}
                <section className="w-full lg:w-5/12 border border-cardBorder bg-white">
                  <div className="border-b border-cardBorder px-4 py-4 sm:px-6">
                    <h2 className="text-xl font-semibold leading-7 text-[#333333]">
                      Email Notifications
                    </h2>
                  </div>
                  <div className="p-4 sm:p-6">
                    <Form
                      form={form}
                      initialValues={settings}
                      onFinish={onFinish}
                      layout="vertical"
                    >
                      <Form.Item
                        label={<Text strong>On Success (DH Admins)</Text>}
                        name="on_success_emails"
                        rules={[
                          {
                            validator: async (_, values) => {
                              if (!values || values.length < 1) {
                                return Promise.reject(
                                  new Error("At least 1 emails"),
                                );
                              }
                            },
                          },
                        ]}
                      >
                        <Select options={admins} mode="multiple" />
                      </Form.Item>
                      <EmailListForm
                        label="On Failure (Technical Support)"
                        name="on_failure_emails"
                      />
                      <EmailListForm
                        label="On Job Exceeded"
                        name="on_exceeded_emails"
                      />

                      <Divider />
                      <h3 className="text-base font-semibold text-[#333333] mb-4">
                        CDI Weight
                      </h3>
                      <Form.Item
                        label="LST Weight"
                        name="lst_weight"
                        rules={[{ required: true }]}
                      >
                        <InputNumber
                          step={0.1}
                          min={0}
                          max={1}
                          placeholder="LST Weight"
                          style={{ width: "50%" }}
                        />
                      </Form.Item>
                      <Form.Item
                        label="NDVI Weight"
                        name="ndvi_weight"
                        rules={[{ required: true }]}
                      >
                        <InputNumber
                          step={0.1}
                          min={0}
                          max={1}
                          placeholder="NDVI Weight"
                          style={{ width: "50%" }}
                        />
                      </Form.Item>
                      <Form.Item
                        label="SPI Weight"
                        name="spi_weight"
                        rules={[{ required: true }]}
                      >
                        <InputNumber
                          step={0.1}
                          min={0}
                          max={1}
                          placeholder="SPI Weight"
                          style={{ width: "50%" }}
                        />
                      </Form.Item>
                      <Form.Item
                        label="SM Weight"
                        name="sm_weight"
                        rules={[{ required: true }]}
                      >
                        <InputNumber
                          step={0.1}
                          min={0}
                          max={1}
                          placeholder="SM Weight"
                          style={{ width: "50%" }}
                        />
                      </Form.Item>
                      <div className="w-full">
                        <Button
                          type="primary"
                          htmlType="submit"
                          size="large"
                          disabled={!submittable}
                          loading={loading}
                          block
                        >
                          Save
                        </Button>
                      </div>
                    </Form>
                  </div>
                </section>

                {/* Right column — Manual Executions */}
                <section className="w-full lg:w-7/12 border border-cardBorder bg-white">
                  <div className="border-b border-cardBorder px-4 py-4 sm:px-6 flex items-center justify-between">
                    <h2 className="text-xl font-semibold leading-7 text-[#333333]">
                      Manual Executions
                    </h2>
                    <Button
                      type="primary"
                      onClick={() => {
                        window.open(
                          `/rundeck/project/${settings?.project_name}/home`,
                          "_blank",
                        );
                      }}
                      ghost
                    >
                      Open Rundeck
                    </Button>
                  </div>
                  <div className="p-4 sm:p-6">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4">
                      {execList?.[0]?.date_started && (
                        <Text type="secondary" className="text-xs">
                          Last executed:{" "}
                          {dayjs
                            .utc(execList[0].date_started)
                            .local()
                            .format("MMMM Do, YYYY - h:mm A")}
                        </Text>
                      )}
                      <div className="ml-auto">
                        <Form
                          onFinish={onRunJob}
                          layout="inline"
                          className="flex items-center gap-2"
                        >
                          <Form.Item
                            name="year_month"
                            label="Publication Date"
                            rules={[{ required: true }]}
                            className="!mb-0"
                          >
                            <DatePicker
                              format={{
                                format: "YYYY-MM",
                                type: "mask",
                              }}
                              picker="month"
                            />
                          </Form.Item>
                          <Button
                            htmlType="submit"
                            type="primary"
                            loading={jobExecuting}
                            disabled={runJobNowIsDisabled}
                          >
                            Run Job Now
                          </Button>
                        </Form>
                      </div>
                    </div>
                    <Divider className="!my-4" />
                    <div className="w-full">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-base font-semibold text-[#333333]">
                          Recent Executions
                        </h3>
                        <Button
                          size="small"
                          onClick={() => setJobChecking(true)}
                        >
                          Refresh
                        </Button>
                      </div>
                      <Table
                        dataSource={execList}
                        rowKey="id"
                        columns={[
                          {
                            key: "id",
                            dataIndex: "id",
                            title: "#",
                          },
                          {
                            key: "year_month",
                            dataIndex: "year_month",
                            title: "PUBLICATION DATE",
                          },
                          {
                            key: "date_started",
                            dataIndex: "date_started",
                            title: "CREATED AT",
                            render: (value) =>
                              dayjs
                                .utc(value)
                                .local()
                                .format("DD/MM/YYYY h:mm A"),
                          },
                          {
                            key: "date_ended",
                            dataIndex: "date_ended",
                            title: "FINISHED AT",
                            render: (value) =>
                              value
                                ? dayjs
                                    .utc(value)
                                    .local()
                                    .format("DD/MM/YYYY h:mm A")
                                : "-",
                          },
                          {
                            key: "status",
                            dataIndex: "status",
                            title: "STATUS",
                            render: (status, { permalink }) => (
                              <a target="_blank" href={permalink}>
                                <Badge
                                  color={RUNDECK_JOB_STATUS_COLOR?.[status]}
                                  text={status}
                                />
                              </a>
                            ),
                          },
                        ]}
                        {...tableProps}
                      />
                    </div>
                  </div>
                </section>
              </div>
            )}
          </Skeleton>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
