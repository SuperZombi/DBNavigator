window.addEventListener("load", _=>{
	document.querySelector("#execute").onclick = executeSQL

	if (window.location.search){
		let params = new URLSearchParams(window.location.search);
		document.querySelector("#query").value = params.get("query")
	}
})

function executeSQL(){
	let query = document.querySelector("#query").value.trim()
	if (query == ""){return}
	document.querySelector("#results").innerHTML = ""

	var xhr = new XMLHttpRequest();
	xhr.open("POST", window.location.href);
	xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8"); 
	xhr.onload = function(){
		if (xhr.status != 200){
			alert(`[${xhr.status}] ${xhr.statusText}`)
		} else{
			let result = JSON.parse(xhr.response)
			if (!result.successfully){
				document.querySelector("#results").innerHTML = `
					<div class="alert alert-danger" role="alert">${result.error}</div>
				`
			} else{
				if (result.data){
					createTable(result.column_names, result.data, result.rowcount)
				} else{
					if (result.total_changes == 0 && READONLY){
						document.querySelector("#results").innerHTML = `
							<div class="alert alert-warning" role="alert">The database is readonly!</div>`
					}
					else{
						document.querySelector("#results").innerHTML = `
							<div class="alert alert-success" role="alert">Successfully changed ${result.total_changes} rows</div>`
					}
				}
				let url = new URL(window.location.href)
				url.searchParams.set("query", query)
				window.history.pushState(null, '', url.href);
			}
		}
	};
	xhr.send(JSON.stringify({"query": query}));
}

function createTable(columns, data, rows_count){
	document.querySelector("#results").innerHTML = `
		<h3>Results (${rows_count})</h3>
	`
	let tableWrap = document.createElement("table")
	tableWrap.className = "table table-striped table-hover text-center"
	let table = document.createElement("tbody")
	let tr = document.createElement("tr")
	columns.forEach(name=>{
		let th = document.createElement("th")
		th.innerHTML = name
		tr.appendChild(th)
	})
	table.appendChild(tr)

	data.forEach(row=>{
		let tr = document.createElement("tr")
		row.forEach(el=>{
			let td = document.createElement("td")
			td.innerHTML = el
			tr.appendChild(td)
		})
		table.appendChild(tr)
	})

	tableWrap.appendChild(table)
	document.querySelector("#results").appendChild(tableWrap)
}
