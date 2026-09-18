var creditText = 'i-SPEED by VNNIC (số liệu được tính theo phương pháp trung vị)';
var creditUrl = 'https://speedtest.vn/';

//var methodCheckBox = document.getElementById('statsmethod');
var typeCheckBox = document.getElementById('internettype');
var enterpriseSelect = document.getElementById('valueIspId');
var provinceSelect = document.getElementById('provinceId');

var ispName = document.getElementById('valueIspId').value;
var provinceId = document.getElementById('provinceId').value;

function drawOverviewMap(network, year, month, isp, cityId, vietmapChart) {
	const colorThresholds = network === 'ftth' ? [100, 140, 180, 220, 260] : [40, 80, 120, 160, 200];
	vietmapChart.setColorThresholds(colorThresholds);
	$.ajax({
		url: '/i-speed/' + network + '/overview-place-map?year=' + year + '&month=' + month + '&isp=' + isp + '&cityId=' + cityId,
		type: 'GET',
		async: false,
		success: function(results) {
			datamaps = results;
			vietmapChart.loadMap(datamaps, cityId);
			console.log(datamaps);
		}
	});
}

drawOverviewMap('ftth', recentYear, recentMonth, ispName, provinceId, vietmapChart);
drawFtthOverviewChart(recentYear, recentMonth, ispName, provinceId, 'bandwidthLatencyChartFtth');
drawFtthCityChart(recentYear, recentMonth, ispName, 'mainCityChartFtth');
drawIspFtthChart(recentYear, recentMonth, ftthIspList, provinceId, '_MedianMonthlyChart');
drawMobileOverviewChart(recentYear, recentMonth, ispName, provinceId, 'bandwidthLatencyChartMobile');
drawMobileCityChart(recentYear, recentMonth, ispName, 'mainCityChartMobile');
drawIspMobileChart(recentYear, recentMonth, mobileIspList, provinceId, '_MedianMonthlyChart');

//change type brdd & brdd
function changeType() {
	enterpriseSelect.selectedIndex = 0;
	provinceSelect.selectedIndex = 0;
	if (typeCheckBox.checked) {
		ftthChangeOptions();
		enterpriseSelect.length = 1;
		for (const k of ftthIspList) {
			enterpriseSelect.options[enterpriseSelect.options.length] = new Option(k, k);
		}
	} else {
		mobileChangeOptions();
		enterpriseSelect.length = 1;
		for (const k of mobileIspList) {
			enterpriseSelect.options[enterpriseSelect.options.length] = new Option(k, k);
		}
	}
	if (typeCheckBox.checked) {
		document.getElementById('mobile-stats').style.display = 'none';
		$('#mobile-charts').hide();
		document.getElementById('ftth-stats').style.display = 'block';
		$('#ftth-charts').show();
	} else {
		document.getElementById('mobile-stats').style.display = 'block';
		$('#mobile-charts').show();
		document.getElementById('ftth-stats').style.display = 'none';
		$('#ftth-charts').hide();
	}
}

function ftthChangeOptions() {
	ispName = document.getElementById('valueIspId').value;
	provinceId = document.getElementById('provinceId').value;
	if (provinceId != -1) {
		$('#mainCityChartFtth').parent().hide();
		$('#mainCityChartMobile').parent().hide();
	} else {
		$('#mainCityChartFtth').parent().show();
		$('#mainCityChartMobile').parent().show();
		drawFtthCityChart(recentYear, recentMonth, ispName, 'mainCityChart' + 'Ftth');
	}

	if (ispName != 'ALL') {
		ftthIspList.forEach(isp => {
			var chartId = '#' + isp.replace(/\s/g, '') + '_MedianMonthlyChart' + 'Ftth';
			$(chartId).parent().hide();
		});
	} else {
		ftthIspList.forEach(isp => {
			var chartId = '#' + isp.replace(/\s/g, '') + '_MedianMonthlyChart' + 'Ftth';
			$(chartId).parent().show();
		});
		drawIspFtthChart(recentYear, recentMonth, ftthIspList, provinceId, '_MedianMonthlyChart');
	}

	drawFtthOverviewChart(recentYear, recentMonth, ispName, provinceId, 'bandwidthLatencyChart' + 'Ftth');
	drawOverviewMap('ftth', recentYear, recentMonth, ispName, provinceId, vietmapChart);
}

function mobileChangeOptions() {
	ispName = document.getElementById('valueIspId').value;
	provinceId = document.getElementById('provinceId').value;
	if (provinceId != -1) {
		$('#mainCityChartFtth').parent().hide();
		$('#mainCityChartMobile').parent().hide();
	} else {
		$('#mainCityChartFtth').parent().show();
		$('#mainCityChartMobile').parent().show();
		drawMobileCityChart(recentYear, recentMonth, ispName, 'mainCityChart' + 'Mobile');
	}

	if (ispName != 'ALL') {
		mobileIspList.forEach(isp => {
			var chartId = '#' + isp.replace(/\s/g, '') + '_MedianMonthlyChart' + 'Mobile';
			$(chartId).parent().hide();
		});
	} else {
		mobileIspList.forEach(isp => {
			var chartId = '#' + isp.replace(/\s/g, '') + '_MedianMonthlyChart' + 'Mobile';
			$(chartId).parent().show();
		});
		drawIspMobileChart(recentYear, recentMonth, mobileIspList, provinceId, '_MedianMonthlyChart');
	}

	drawMobileOverviewChart(recentYear, recentMonth, ispName, provinceId, 'bandwidthLatencyChart' + 'Mobile');
	drawOverviewMap('mobile', recentYear, recentMonth, ispName, provinceId, vietmapChart);
}


provinceSelect.onchange = function() {
	if (typeCheckBox.checked) {
		ftthChangeOptions();
	} else {
		mobileChangeOptions();
	}
}

enterpriseSelect.onchange = function() {
	if (typeCheckBox.checked) {
		ftthChangeOptions();
	} else {
		mobileChangeOptions();
	}
}

//FTTH CHARTS
function drawFtthOverviewChart(year, month, isp, cityId, chartId) {
	$.ajax({
		url: '/i-speed/ftth/overview-monthly-chart?year=' + year + '&month=' + month + '&isp=' + isp + '&cityId=' + cityId,
		type: 'GET',
		success: function(results) {

			var chartResponse = results;
			var categories = chartResponse.categories;
			var datasets = chartResponse.series;
			var chartTitle = 'Tốc độ, độ trễ mạng BRCĐ';
			if (isp != 'ALL') {
				chartTitle += ' của doanh nghiệp ' + isp;
			}
			if (cityId != -1) {
				var cityName = cityList.find((element) => element.id == cityId).shortName;
				chartTitle += ' tại ' + cityName;
			} else {
				chartTitle += ' trên cả nước';
			}

			Highcharts.chart(chartId, {
				chart: {
					type: 'spline'
				},
				title: {
					text: chartTitle
				},
				xAxis: {
					crosshair: true,
					categories: categories,
					labels: {
						enabled: true,
						rotation: 0,
						align: 'center',
						overflow: 'allow',
						formatter: function() {
							if (this.isLast || this.isFirst) {
								return this.value.split(":")[0];
							}
						}
					},
					gridLineWidth: 1
				},
				yAxis: [
					{
						title: {
							enabled: true,
							text: 'Tốc độ'
						},
						min: 0,
						lineWidth: 1,
						gridLineDashStyle: 'longdash',
						labels: {
							format: '{value} Mbps'
						},
						height: "55%"
					},
					{
						title: {
							enabled: true,
							text: 'Độ trễ'
						},
						min: 0,
						lineWidth: 1,
						gridLineDashStyle: 'longdash',
						labels: {
							format: '{value} ms'
						},
						// opposite: true,
						offset: 0,
						top: "65%",
						height: "35%"
					},
					{
						min: 0,
						max: 0,
						tickPositions: [],
					}
				],
				tooltip: {
					shared: true,
					pointFormatter: function() {
						if (this.y == 0) {
							return `<span style="color:${this.series.color}">\u25CF</span>${this.series.name} : Không đủ số mẫu để đánh giá!<br/>`
						}
						else {
							return `<span style="color:${this.series.color}">\u25CF</span> ${this.series.name} : ${this.y} ${this.series.tooltipOptions.valueSuffix}<br/>`
						}
					}
				},
				colors: ['#133C8B', '#ee3d85', '#7cb5ec', '#434348'],
				series: [
					{
						name: datasets[0].name,
						data: datasets[0].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[1].name,
						data: datasets[1].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[2].name,
						data: datasets[2].data,
						tooltip: {
							valueSuffix: ' ms'
						},
						yAxis: 1
					},
					{
						name: datasets[3].name,
						data: datasets[3].data,
						tooltip: {
							valueSuffix: ' ms'
						},
						yAxis: 2,
						showInLegend: false
					}
				],
				exporting: {
					enabled: false
				}
			});

		}
	});

}

function drawFtthCityChart(year, month, isp, chartId) {
	$.ajax({
		url: '/i-speed/ftth/main-city-monthly-chart?year=' + year + '&month=' + month + '&isp=' + isp,
		type: 'GET',
		success: function(results) {

			var chartResponse = results;
			var categories = chartResponse.categories;
			var datasets = chartResponse.series;

			var chartTitle = 'Tốc độ, độ trễ mạng BRCĐ';
			if (isp != 'ALL') {
				chartTitle += ' của doanh nghiệp ' + isp;
			}
			chartTitle += ' tại một số tỉnh, thành phố';

			Highcharts.chart(chartId, {
				chart: {
					type: 'spline',
					borderWidth: 0,
					spacingRight: 40
				},
				title: {
					text: chartTitle
				},
				xAxis: {
					crosshair: true,
					categories: categories,
					labels: {
						enabled: true,
						rotation: 0,
						align: 'center',
						overflow: 'allow',
						formatter: function() {
							if (this.isLast || this.isFirst) {
								return this.value.split(":")[0];
							}
						}
					},
					gridLineWidth: 1
				},
				yAxis: [
					{
						title: {
							enabled: true,
							text: 'Tốc độ'
						},
						lineWidth: 1,
						gridLineDashStyle: 'longdash',
						labels: {
							format: '{value} Mbps'
						}
					},
					{
						min: 0,
						max: 0,
						tickPositions: [],
					}
				],
				tooltip: {
					shared: true,
					pointFormatter: function() {
						if (this.y == 0) {
							return `<span style="color:${this.series.color}">\u25CF</span>${this.series.name} : Không đủ số mẫu để đánh giá!<br/>`
						}
						else {
							return `<span style="color:${this.series.color}">\u25CF</span> ${this.series.name} : ${this.y} ${this.series.tooltipOptions.valueSuffix}<br/>`
						}
					}
				},

				series: [
					{
						name: datasets[0].name,
						data: datasets[0].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[1].name,
						data: datasets[1].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[2].name,
						data: datasets[2].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[3].name,
						data: datasets[3].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[4].name,
						data: datasets[4].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					}
				],
				exporting: {
					enabled: false
				}
			});
		}
	});
}

function drawIspFtthChart(year, month, ispList, cityId, suffixChartId) {
	$.ajax({
		url: '/i-speed/ftth/isp-by-province-chart?year=' + year + '&month=' + month + '&cityId=' + cityId,
		type: 'GET',
		success: function(results) {

			ispList.forEach((isp) => {

				var chartId = isp.replace(/\s/g, '') + suffixChartId;
				var chartResponse = results[chartId];
				var categories = chartResponse.categories;
				var datasets = chartResponse.series;

				var chartTitle = 'Tốc độ, độ trễ mạng BRCĐ';
				if (isp != 'ALL') {
					chartTitle += ' của doanh nghiệp ' + isp;
				}
				if (cityId != -1) {
					var cityName = cityList.find((element) => element.id == cityId).shortName;
					chartTitle += ' tại ' + cityName;
				} else {
					chartTitle += ' trên cả nước';
				}

				Highcharts.chart(chartId + "Ftth", {
					chart: {
						type: 'spline',
						borderWidth: 0,
						spacingRight: 40
					},
					title: {
						text: chartTitle
					},
					xAxis: {
						crosshair: true,
						categories: categories,
						labels: {
							enabled: true,
							rotation: 0,
							align: 'center',
							overflow: 'allow',
							formatter: function() {
								if (this.isLast || this.isFirst) {
									return this.value.split(":")[0];
								}
							}
						},
						gridLineWidth: 1
					},
					yAxis: [
						{
							title: {
								enabled: true,
								text: 'Tốc độ'
							},
							min: 0,
							lineWidth: 1,
							gridLineDashStyle: 'longdash',
							labels: {
								format: '{value} Mbps'
							},
							height: "55%"
						},
						{
							title: {
								enabled: true,
								text: 'Độ trễ'
							},
							min: 0,
							lineWidth: 1,
							gridLineDashStyle: 'longdash',
							labels: {
								format: '{value} ms'
							},
							// opposite: true,
							offset: 0,
							top: "65%",
							height: "35%"
						},
						{
							min: 0,
							max: 0,
							tickPositions: [],
						}
					],
					tooltip: {
						shared: true,
						pointFormatter: function() {
							if (this.y == 0) {
								return `<span style="color:${this.series.color}">\u25CF</span>${this.series.name} : Không đủ số mẫu để đánh giá!<br/>`
							}
							else {
								return `<span style="color:${this.series.color}">\u25CF</span> ${this.series.name} : ${this.y} ${this.series.tooltipOptions.valueSuffix}<br/>`
							}
						}
					},
					colors: ['#133C8B', '#ee3d85', '#7cb5ec', '#434348'],
					series: [
						{
							name: datasets[0].name,
							data: datasets[0].data,
							tooltip: {
								valueSuffix: ' Mbps'
							}
						},
						{
							name: datasets[1].name,
							data: datasets[1].data,
							tooltip: {
								valueSuffix: ' Mbps'
							}
						},
						{
							name: datasets[2].name,
							data: datasets[2].data,
							tooltip: {
								valueSuffix: ' ms'
							},
							yAxis: 1
						},
						{
							name: datasets[3].name,
							data: datasets[3].data,
							tooltip: {
								valueSuffix: ' ms'
							},
							yAxis: 2,
							showInLegend: false
						}
					],
					exporting: {
						enabled: false
					}
				});
			});

		}
	});
}

//MOBILE CHARTS
function drawMobileOverviewChart(year, month, isp, cityId, chartId) {
	$.ajax({
		url: '/i-speed/mobile/overview-monthly-chart?year=' + year + '&month=' + month + '&isp=' + isp + '&cityId=' + cityId,
		type: 'GET',
		success: function(results) {

			var chartResponse = results;
			var categories = chartResponse.categories;
			var datasets = chartResponse.series;

			var chartTitle = 'Tốc độ, độ trễ mạng BRDĐ';
			if (isp != 'ALL') {
				chartTitle += ' của doanh nghiệp ' + isp;
			}
			if (cityId != -1) {
				var cityName = cityList.find((element) => element.id == cityId).shortName;
				chartTitle += ' tại ' + cityName;
			} else {
				chartTitle += ' trên cả nước';
			}

			Highcharts.chart(chartId, {
				chart: {
					type: 'spline',
					borderWidth: 0,
					spacingRight: 40
				},
				title: {
					text: chartTitle
				},
				xAxis: {
					crosshair: true,
					categories: categories,
					labels: {
						enabled: true,
						rotation: 0,
						align: 'center',
						overflow: 'allow',
						formatter: function() {
							if (this.isLast || this.isFirst) {
								return this.value.split(":")[0];
							}
						}
					},
					gridLineWidth: 1
				},
				yAxis: [
					{
						title: {
							enabled: true,
							text: 'Tốc độ'
						},
						min: 0,
						lineWidth: 1,
						gridLineDashStyle: 'longdash',
						labels: {
							format: '{value} Mbps'
						},
						height: "55%"
					},
					{
						title: {
							enabled: true,
							text: 'Độ trễ'
						},
						min: 0,
						lineWidth: 1,
						gridLineDashStyle: 'longdash',
						labels: {
							format: '{value} ms'
						},
						// opposite: true,
						offset: 0,
						top: "65%",
						height: "35%"
					},
					{
						min: 0,
						max: 0,
						tickPositions: [],
					}
				],
				tooltip: {
					shared: true,
					pointFormatter: function() {
						if (this.y == 0) {
							return `<span style="color:${this.series.color}">\u25CF</span>${this.series.name} : Không đủ số mẫu để đánh giá!<br/>`
						}
						else {
							return `<span style="color:${this.series.color}">\u25CF</span> ${this.series.name} : ${this.y} ${this.series.tooltipOptions.valueSuffix}<br/>`
						}
					}
				},
				colors: ['#133C8B', '#ee3d85', '#7cb5ec', '#434348'],
				series: [
					{
						name: datasets[0].name,
						data: datasets[0].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[1].name,
						data: datasets[1].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[2].name,
						data: datasets[2].data,
						tooltip: {
							valueSuffix: ' ms'
						},
						yAxis: 1
					},
					{
						name: datasets[3].name,
						data: datasets[3].data,
						tooltip: {
							valueSuffix: ' ms'
						},
						yAxis: 2,
						showInLegend: false
					}
				],
				exporting: {
					enabled: false
				}
			});

		}
	});

}

function drawMobileCityChart(year, month, isp, chartId) {
	$.ajax({
		url: '/i-speed/mobile/main-city-monthly-chart?year=' + year + '&month=' + month + '&isp=' + isp,
		type: 'GET',
		success: function(results) {

			var chartResponse = results;
			var categories = chartResponse.categories;
			var datasets = chartResponse.series;

			var chartTitle = 'Tốc độ, độ trễ mạng BRDĐ';
			if (isp != 'ALL') {
				chartTitle += ' của doanh nghiệp ' + isp;
			}
			chartTitle += ' tại một số tỉnh, thành phố';

			Highcharts.chart(chartId, {
				chart: {
					type: 'spline',
					borderWidth: 0,
					spacingRight: 40
				},
				title: {
					text: chartTitle
				},
				xAxis: {
					crosshair: true,
					categories: categories,
					labels: {
						enabled: true,
						rotation: 0,
						align: 'center',
						overflow: 'allow',
						formatter: function() {
							if (this.isLast || this.isFirst) {
								return this.value.split(":")[0];
							}
						}
					},
					gridLineWidth: 1
				},
				yAxis: [
					{
						title: {
							enabled: true,
							text: 'Tốc độ'
						},
						lineWidth: 1,
						gridLineDashStyle: 'longdash',
						labels: {
							format: '{value} Mbps'
						}
					},
					{
						min: 0,
						max: 0,
						tickPositions: [],
					}
				],
				tooltip: {
					shared: true,
					pointFormatter: function() {
						if (this.y == 0) {
							return `<span style="color:${this.series.color}">\u25CF</span>${this.series.name} : Không đủ số mẫu để đánh giá!<br/>`
						}
						else {
							return `<span style="color:${this.series.color}">\u25CF</span> ${this.series.name} : ${this.y} ${this.series.tooltipOptions.valueSuffix}<br/>`
						}
					}
				},

				series: [
					{
						name: datasets[0].name,
						data: datasets[0].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[1].name,
						data: datasets[1].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[2].name,
						data: datasets[2].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[3].name,
						data: datasets[3].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					},
					{
						name: datasets[4].name,
						data: datasets[4].data,
						tooltip: {
							valueSuffix: ' Mbps'
						}
					}
				],
				exporting: {
					enabled: false
				}
			});
		}
	});
}

function drawIspMobileChart(year, month, ispList, cityId, suffixChartId) {
	$.ajax({
		url: '/i-speed/mobile/isp-by-province-chart?year=' + year + '&month=' + month + '&cityId=' + cityId,
		type: 'GET',
		success: function(results) {

			ispList.forEach((isp) => {

				var chartId = isp.replace(/\s/g, '') + suffixChartId;
				var chartResponse = results[chartId];
				var categories = chartResponse.categories;
				var datasets = chartResponse.series;

				var chartTitle = 'Tốc độ, độ trễ mạng BRDĐ';
				if (isp != 'ALL') {
					chartTitle += ' của doanh nghiệp ' + isp;
				}
				if (cityId != -1) {
					var cityName = cityList.find((element) => element.id == cityId).shortName;
					chartTitle += ' tại ' + cityName;
				} else {
					chartTitle += ' trên cả nước';
				}

				Highcharts.chart(chartId + "Mobile", {
					chart: {
						type: 'spline',
						borderWidth: 0,
						spacingRight: 40
					},
					title: {
						text: chartTitle
					},
					xAxis: {
						crosshair: true,
						categories: categories,
						labels: {
							enabled: true,
							rotation: 0,
							align: 'center',
							overflow: 'allow',
							formatter: function() {
								if (this.isLast || this.isFirst) {
									return this.value.split(":")[0];
								}
							}
						},
						gridLineWidth: 1
					},
					yAxis: [
						{
							title: {
								enabled: true,
								text: 'Tốc độ'
							},
							min: 0,
							lineWidth: 1,
							gridLineDashStyle: 'longdash',
							labels: {
								format: '{value} Mbps'
							},
							height: "55%"
						},
						{
							title: {
								enabled: true,
								text: 'Độ trễ'
							},
							min: 0,
							lineWidth: 1,
							gridLineDashStyle: 'longdash',
							labels: {
								format: '{value} ms'
							},
							// opposite: true,
							offset: 0,
							top: "65%",
							height: "35%"
						},
						{
							min: 0,
							max: 0,
							tickPositions: [],
						}
					],
					tooltip: {
						shared: true,
						pointFormatter: function() {
							if (this.y == 0) {
								return `<span style="color:${this.series.color}">\u25CF</span>${this.series.name} : Không đủ số mẫu để đánh giá!<br/>`
							}
							else {
								return `<span style="color:${this.series.color}">\u25CF</span> ${this.series.name} : ${this.y} ${this.series.tooltipOptions.valueSuffix}<br/>`
							}
						}
					},
					colors: ['#133C8B', '#ee3d85', '#7cb5ec', '#434348'],
					series: [
						{
							name: datasets[0].name,
							data: datasets[0].data,
							tooltip: {
								valueSuffix: ' Mbps'
							}
						},
						{
							name: datasets[1].name,
							data: datasets[1].data,
							tooltip: {
								valueSuffix: ' Mbps'
							}
						},
						{
							name: datasets[2].name,
							data: datasets[2].data,
							tooltip: {
								valueSuffix: ' ms'
							},
							yAxis: 1
						},
						{
							name: datasets[3].name,
							data: datasets[3].data,
							tooltip: {
								valueSuffix: ' ms'
							},
							yAxis: 2,
							showInLegend: false
						}
					],
					exporting: {
						enabled: false
					}
				});
			});

		}
	});
}

/*
function loadDatamaps(network, year, month, isp, cityId) {
	$.ajax({
		url: '/i-speed/' + network + '/overview-place-map?year=' + year + '&month=' + month + '&isp=' + isp + '&cityId=' + cityId,
		type: 'GET',
		async: false,
		success: function(results) {
			datamaps = results;
			var group1 = [];
			var group2 = [];
			var group3 = [];
			var group4 = [];
			var group5 = [];
			var group6 = [];
			if (network == 'ftth') {
				datamaps.forEach(element => {
					var value = element.download;
					if (value <= 100) {
						group1.push(element.code);
					} else if (value > 100 && value <= 140) {
						group2.push(element.code);
					} else if (value > 140 && value <= 180) {
						group3.push(element.code);
					} else if (value > 180 && value <= 220) {
						group4.push(element.code);
					} else if (value > 220 && value <= 260) {
						group5.push(element.code);
					} else if (value > 260) {
						group6.push(element.code);
					}
				});
			} else {
				datamaps.forEach(element => {
					var value = element.download;
					if (value <= 40) {
						group1.push(element.code);
					} else if (value > 40 && value <= 60) {
						group2.push(element.code);
					} else if (value > 60 && value <= 80) {
						group3.push(element.code);
					} else if (value > 80 && value <= 100) {
						group4.push(element.code);
					} else if (value > 100 && value <= 120) {
						group5.push(element.code);
					} else if (value > 120) {
						group6.push(element.code);
					}
				});
			}

			fillColor = [
				"case",
				["in", ["get", "code"], ["literal", group1]], "rgba(211,63,79,1)",
				["in", ["get", "code"], ["literal", group2]], "rgba(249,106,72,1)",
				["in", ["get", "code"], ["literal", group3]], "rgba(255,170,100,1)",
				["in", ["get", "code"], ["literal", group4]], "rgba(171,224,154,1)",
				["in", ["get", "code"], ["literal", group5]], "rgba(99,193,166,1)",
				["in", ["get", "code"], ["literal", group6]], "rgba(43,138,196,1)",
				"rgba(211, 211, 211, 1)"
			];
		}
	});
}
*/