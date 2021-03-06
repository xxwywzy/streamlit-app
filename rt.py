import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use('seaborn-white')

import epyestim
import epyestim.covid19 as covid19
import datetime

from scipy.stats import gamma, poisson


st.markdown('# COVID-19 有效传染数估计')
# 等同于 title

# 数据载入模块（多行注释会展示出来）
# 当前提供两种数据载入方式
# 1. 自动下载全球每日病例病例
# 2. 手动上传病例数据（目前只支持深圳市数据）
st.markdown('## 数据载入')

DATA_URL = ('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/'
            'csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv')

# 读取全球病例数据并进行预处理
@st.cache
def load_data():
    df_data = pd.read_csv(DATA_URL)
    df_data = df_data.fillna("")
    df_data['地区'] = df_data['Country/Region'] + " " + df_data['Province/State']
    df_data['地区'] = df_data['地区'].str.strip()
    df_data.drop(columns=['Province/State', 'Country/Region', 'Lat', 'Long'], inplace=True)
    df_final =pd.melt(df_data,id_vars='地区',var_name='日期',value_name='总数')
    df_final['日期'] = pd.to_datetime(df_final['日期']).dt.date
    return df_final

# 针对中文格式的日期进行转换
def date_chn(x):
    x = x.str.split('日').str[0].add('日')
    x = x.str.replace('年', '-').str.replace('月', '-').str.replace('日', '')
    x = pd.to_datetime(x, format='%Y-%m-%d', errors='coerce').dt.date
    return x

#处理手动上传的病例数据
@st.cache
def process_upload_data(df):
    df[['jzrq']] = df[['jzrq']].apply(date_chn)
    df = df.groupby('jzrq')['xzqz'].sum().reset_index(name="每日新增")
    df.rename(columns={"jzrq": "日期"}, inplace=True)
    df['地区'] = '深圳'
    return df

option = st.selectbox(
     '请选择数据源',
     ('全球每日病例数据', '手动上传数据', '社会面与总量对比'))

# data = pd.DataFrame(columns=['地区', '日期', '总数'])
data = load_data()

if option == '全球每日病例数据':
    data_load_state = st.text('正在下载数据...')
    global_data = load_data()
    data = global_data
    data_load_state.text("COVID-19 全球每日病例数据下载处理完成")

elif option == '手动上传数据':
    uploaded_file = st.file_uploader("请选择 csv 文件")
    if uploaded_file is not None:
        upload_data = pd.read_csv(uploaded_file)
        upload_data = process_upload_data(upload_data)
        data = upload_data

elif option == '社会面与总量对比':
    uploaded_file = st.file_uploader("请选择 excel 文件")
    dtype = st.radio(
     "请选择传染数计算所基于的数据类型",
     ('总病例数', '社会面病例'))

    if uploaded_file is not None:
        upload_data = pd.read_excel(uploaded_file)
        upload_data['报告时间'] = pd.to_datetime(upload_data['报告时间']).dt.date
        if dtype == '社会面病例':
            upload_data.drop(columns=['总病例数'], inplace=True)
            upload_data.rename(columns={"报告时间": "日期", "社会面病例": "每日新增"}, inplace=True)
        else:
            upload_data.drop(columns=['社会面病例'], inplace=True)
            upload_data.rename(columns={"报告时间": "日期", "总病例数": "每日新增"}, inplace=True)
        upload_data['地区'] = '北京'
        data = upload_data
        # upload_data = process_upload_data(upload_data)
        # data = upload_data

if st.checkbox('查看原始数据'):
    st.markdown('### 原始数据')
    st.dataframe(data)



st.markdown('## 计算有效传染数 $R_t$')

st.markdown('### 设置输入分布')

fig, axs = plt.subplots(1, 2, figsize=(12,3))

si_distrb = covid19.generate_standard_si_distribution()
delay_distrb = covid19.generate_standard_infection_to_reporting_distribution()

axs[0].bar(range(len(si_distrb)), si_distrb, width=1)
axs[1].bar(range(len(delay_distrb)), delay_distrb, width=1)

axs[0].set_title('Default serial interval distribution')
axs[1].set_title('Default infection-to-reporting delay distribution')


# dpi在这里设置
if st.checkbox('使用默认分布'):
    st.pyplot(fig, dpi=500)
    use_si_distrb = si_distrb
else:
    st.markdown('#### 自定义 SI 分布')
    left, right = st.columns(2)

    with left:
        mean_si= st.number_input('请输入 mean_si', value=3.03)

    with right:
        std_si= st.number_input('请输入 std_si', value=1.93)

    my_continuous_distrb = gamma(a=mean_si, scale=std_si)
    my_discrete_distrb = epyestim.discrete_distrb(my_continuous_distrb)

    use_si_distrb = my_discrete_distrb

    st.bar_chart(my_discrete_distrb)


st.markdown('### 相关参数设置')

st.markdown('👈🏻 请在侧边栏进行相关参数设置')

region = st.sidebar.selectbox(
    '请选择国家地区',
     data['地区'].unique()) # 下拉框支持列表、字典、Series

df_region = data[data['地区'] == region]
df_region = df_region.sort_values(by=['日期'])
df_region = df_region.reset_index(drop=True)

# 在筛选范围前计算每日增量
@st.cache
def calculate_add(df_region):
    if '总数' in df_region.columns:
        for index, row in df_region.iterrows():
            if index == 0:
                df_region.loc[index, "每日新增"] = row['总数']
            else:
                previous_count = df_region.loc[index - 1, "总数"]
                cnt = row['总数'] - previous_count
                if cnt >= 0:
                    df_region.loc[index, "每日新增"] = cnt
                else:
                    df_region.loc[index, "每日新增"] = 0

        df_region['每日新增'] = df_region['每日新增'].astype(int)

    return df_region

df_region = calculate_add(df_region)

# 选择时间范围
start_day = st.sidebar.date_input(
     "请选择病例数据起始时间",
     datetime.date(2022, 1, 1))

end_day = st.sidebar.date_input(
     "请选择病例数据结束时间",
     df_region['日期'].max())

df_region = df_region[(df_region['日期'] >= start_day) & (df_region['日期'] <= end_day)]


left_column, right_column = st.columns(2)

with left_column:
    st.write('当前选择地区', region)

with right_column:
    st.write('当前选择时间范围', start_day, "-", end_day)

if st.checkbox('查看当前地区的病例数据'):
    st.dataframe(df_region)


st.markdown('### 有效传染数估计')

smoothing_window= st.sidebar.number_input('请设置 LOWESS 平滑窗口大小', value=14)

r_window= st.sidebar.number_input('请设置移动平均窗口大小', value=7)

fig_r, ax_r = plt.subplots(1,1, figsize=(12, 4))


@st.cache
def get_R_result(df_region):
    ch_cases_region = df_region.set_index('日期')['每日新增']
    ch_time_varying_r = covid19.r_covid(ch_cases_region,
        gt_distribution = use_si_distrb,
        smoothing_window=smoothing_window, r_window_size=r_window)
    return ch_time_varying_r

ch_time_varying_r = get_R_result(df_region)


if st.checkbox('查看原始结果'):
    st.write(ch_time_varying_r)

st.markdown("#### 有效传染数时间分布曲线")

ch_time_varying_r.loc[:,'Q0.5'].plot(ax=ax_r, color='red')
ax_r.fill_between(ch_time_varying_r.index, 
                    ch_time_varying_r['Q0.025'], 
                    ch_time_varying_r['Q0.975'], 
                    color='red', alpha=0.2)
ax_r.set_xlabel('date')
ax_r.set_ylabel('R(t) with 95%-CI')
ax_r.set_ylim([0,ch_time_varying_r['R_mean'].max() + 0.5])
ax_r.axhline(y=1)
ax_r.set_title('Estimate of time-varying effective reproduction number for ' + region)

st.pyplot(fig_r, dpi=500)
